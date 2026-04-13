"""
Background scheduler for L.O.O.M. recurring jobs.
Uses APScheduler with a simple MemoryJobStore (our SQLite is the source of truth).
On startup: loads all enabled jobs from DB and registers them.
"""
import asyncio
import logging
import subprocess
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from tzlocal import get_localzone

from core.task_logger import (
    get_all_jobs, update_job_run_times, log_task_run, get_job_by_id
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

_local_tz = get_localzone()
_scheduler = BackgroundScheduler(timezone=_local_tz)
_started = False


def _run_job(job_id: int):
    """Synchronous wrapper executed by APScheduler in a thread."""
    from core.orchestrator import processUserRequest
    from core.state import globalState

    job = get_job_by_id(job_id)
    if not job or not job["enabled"]:
        return

    logging.info(f"⏰ Running scheduled job [{job['name']}]: {job['prompt'][:60]}")

    accumulated: list[str] = []
    tool_calls: list[dict] = []

    def job_emit(msg: str):
        if msg.startswith("__dag__"):
            import json
            try:
                data = json.loads(msg[len("__dag__"):])
                if data.get("type") == "tool":
                    tool_calls.append({"name": data["name"], "result": data.get("result", "")})
            except Exception:
                pass
        elif not msg.startswith("__"):
            accumulated.append(msg)

    t0 = time.monotonic()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(processUserRequest(job["prompt"], emit=job_emit))
        loop.close()
        status = "done"
    except Exception as e:
        logging.error(f"Scheduled job '{job['name']}' failed: {e}")
        accumulated = [f"Job failed: {e}"]
        status = "failed"

    duration_ms = int((time.monotonic() - t0) * 1000)
    result_text = " ".join(accumulated).strip() or "Job completed with no output."

    log_task_run(
        user_input=f"[SCHEDULED] {job['prompt']}",
        agent="scheduled",
        plan="",
        tool_calls=tool_calls,
        result=result_text,
        status=status,
        duration_ms=duration_ms,
        job_id=job_id,
    )

    now = datetime.now().isoformat(timespec="seconds")
    apjob = _scheduler.get_job(f"job_{job_id}")
    next_run = apjob.next_run_time.isoformat(timespec="seconds") if apjob and apjob.next_run_time else None
    update_job_run_times(job_id, now, next_run)

    # Notify: desktop notification always
    try:
        subprocess.Popen(
            ["notify-send", f"L.O.O.M. — {job['name']}", result_text[:200]],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

    # TTS if voice mode is on
    if globalState.voiceMode:
        try:
            from interfaces.voice.tts_piper import speak
            speak(result_text)
        except Exception:
            pass


def _register_job(job: dict):
    try:
        cron_parts = job["cron"].split()
        if len(cron_parts) == 5:
            minute, hour, day, month, day_of_week = cron_parts
        else:
            logging.warning(f"Invalid cron for job {job['id']}: {job['cron']}")
            return

        _scheduler.add_job(
            _run_job,
            trigger=CronTrigger(
                minute=minute, hour=hour,
                day=day, month=month, day_of_week=day_of_week,
                timezone=_local_tz,
            ),
            args=[job["id"]],
            id=f"job_{job['id']}",
            replace_existing=True,
        )
        logging.info(f"⏰ Scheduled job [{job['name']}] → {job['cron']}")
    except Exception as e:
        logging.error(f"Failed to schedule job {job['id']}: {e}")


def start_scheduler():
    global _started
    if _started:
        return
    _scheduler.start()
    _started = True
    jobs = get_all_jobs()
    for job in jobs:
        if job["enabled"]:
            _register_job(job)
    logging.info(f"⏰ Job scheduler started — {sum(1 for j in jobs if j['enabled'])} jobs loaded")


def add_job_to_scheduler(job: dict):
    if not _started:
        return
    if job["enabled"]:
        _register_job(job)


def remove_job_from_scheduler(job_id: int):
    if not _started:
        return
    try:
        _scheduler.remove_job(f"job_{job_id}")
    except Exception:
        pass


def pause_job_in_scheduler(job_id: int):
    if not _started:
        return
    try:
        _scheduler.pause_job(f"job_{job_id}")
    except Exception:
        pass


def resume_job_in_scheduler(job_id: int):
    if not _started:
        return
    try:
        _scheduler.resume_job(f"job_{job_id}")
    except Exception:
        pass


def get_next_run(job_id: int) -> str | None:
    if not _started:
        return None
    try:
        apjob = _scheduler.get_job(f"job_{job_id}")
        if apjob and apjob.next_run_time:
            return apjob.next_run_time.isoformat(timespec="seconds")
    except Exception:
        pass
    return None
