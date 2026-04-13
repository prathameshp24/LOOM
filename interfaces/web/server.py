import asyncio
import json
import sys
import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from sse_starlette.sse import EventSourceResponse

# Ensure project root is on path when run as a module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.orchestrator import processUserRequest
from core.state import globalState, LOCAL_MODEL

app = FastAPI()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.on_event("startup")
async def startup():
    """Warm up Ollama and start the job scheduler."""
    async def _ping():
        try:
            await asyncio.to_thread(
                globalState.ollamaClient.chat.completions.create,
                model=LOCAL_MODEL,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
                extra_body={"think": False},
            )
            import logging; logging.getLogger().info("✅ Ollama Qwen3 warmed up")
        except Exception as e:
            import logging; logging.getLogger().warning(f"⚠️  Ollama warmup skipped (not running?): {e}")
    asyncio.create_task(_ping())

    from core.job_scheduler import start_scheduler
    await asyncio.to_thread(start_scheduler)


class ChatRequest(BaseModel):
    message: str


class ModeRequest(BaseModel):
    mode: str


class VoiceModeRequest(BaseModel):
    enabled: bool


@app.post("/api/mode")
async def set_mode(req: ModeRequest):
    globalState.switchMode(req.mode)
    return {"mode": globalState.mode}


@app.get("/api/status")
async def get_status():
    from interfaces.voice.wake_word import is_running as ww_running
    return {
        "mode": globalState.mode,
        "voiceMode": globalState.voiceMode,
        "wakeWordActive": ww_running(),
    }


@app.post("/api/voice")
async def transcribe_audio(request: Request):
    """Accepts raw audio/webm from browser MediaRecorder. Returns {"text": "..."}."""
    audio_bytes = await request.body()
    if not audio_bytes:
        return {"text": ""}
    from interfaces.voice.stt_whisper import transcribeAudioBytes
    text = await asyncio.to_thread(transcribeAudioBytes, audio_bytes)
    return {"text": text}


@app.post("/api/voice-mode")
async def set_voice_mode(req: VoiceModeRequest):
    globalState.voiceMode = req.enabled
    return {"voiceMode": globalState.voiceMode}


@app.get("/api/voice-mode")
async def get_voice_mode():
    return {"voiceMode": globalState.voiceMode}


@app.post("/api/wake-word")
async def set_wake_word(req: VoiceModeRequest):
    """Start or stop the background wake word detection thread."""
    from interfaces.voice import wake_word
    if req.enabled:
        await asyncio.to_thread(wake_word.start)
    else:
        wake_word.stop()
    return {"wakeWordActive": wake_word.is_running()}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    queue: asyncio.Queue = asyncio.Queue()
    accumulated_text: list[str] = []

    def emit(msg: str):
        if not msg.startswith("__") and msg.strip():
            accumulated_text.append(msg)
        queue.put_nowait(msg)

    async def run_and_signal():
        try:
            await processUserRequest(req.message, emit)
            if globalState.voiceMode and accumulated_text:
                from interfaces.voice.tts_piper import speak
                speak(" ".join(accumulated_text))  # Popen → non-blocking
        except Exception as e:
            await queue.put(f"Error: {e}")
        finally:
            await queue.put(None)  # sentinel — always sent, even on error

    asyncio.create_task(run_and_signal())

    async def generator():
        while True:
            item = await queue.get()
            if item is None:
                yield {"event": "done", "data": ""}
                break
            if item.startswith("__status__"):
                yield {"event": "status", "data": item[len("__status__"):]}
            elif item.startswith("__dag__"):
                yield {"event": "dag", "data": item[len("__dag__"):]}
            else:
                yield {"event": "message", "data": json.dumps({"text": item})}

    return EventSourceResponse(generator())


@app.get("/habits")
async def habits_page():
    return FileResponse(os.path.join(STATIC_DIR, "habits.html"))


# ── Habit endpoints ───────────────────────────────────────────────────────────

class HabitCreate(BaseModel):
    name: str
    description: str = ""
    color: str = "#00d4ff"
    frequency_per_week: int = 7
    goal_days: Optional[int] = None


class CheckinRequest(BaseModel):
    note: str = ""


@app.get("/api/habits")
async def list_habits():
    from core.habit_manager import getAllHabits
    return await asyncio.to_thread(getAllHabits)


@app.post("/api/habits")
async def create_habit(req: HabitCreate):
    from core.habit_manager import createHabit
    try:
        habit = await asyncio.to_thread(
            createHabit, req.name, req.description, req.color,
            req.frequency_per_week, req.goal_days
        )
        return habit
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/habits/{habit_id}/checkin")
async def checkin_habit(habit_id: int, req: CheckinRequest):
    from core.habit_manager import logHabitById
    result = await asyncio.to_thread(logHabitById, habit_id, req.note)
    return {"message": result}


@app.delete("/api/habits/{habit_id}")
async def delete_habit(habit_id: int):
    from core.habit_manager import deleteHabitById
    await asyncio.to_thread(deleteHabitById, habit_id)
    return {"ok": True}


@app.get("/api/habits/{habit_id}/logs")
async def get_habit_logs(habit_id: int):
    from core.habit_manager import getHabitLogs
    return await asyncio.to_thread(getHabitLogs, habit_id, 14)


# ── Jobs page ─────────────────────────────────────────────────────────────────

@app.get("/jobs")
async def jobs_page():
    return FileResponse(os.path.join(STATIC_DIR, "jobs.html"))


# ── Task runs ─────────────────────────────────────────────────────────────────

@app.get("/api/task-runs")
async def list_task_runs():
    from core.task_logger import get_task_runs
    return await asyncio.to_thread(get_task_runs, 50)


@app.delete("/api/task-runs/{run_id}")
async def delete_task_run_endpoint(run_id: int):
    from core.task_logger import delete_task_run
    await asyncio.to_thread(delete_task_run, run_id)
    return {"ok": True}


# ── Scheduled jobs ────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    name: str
    prompt: str
    cron: str
    schedule_human: str


class JobToggle(BaseModel):
    enabled: bool


@app.get("/api/jobs")
async def list_jobs():
    from core.task_logger import get_all_jobs
    from core.job_scheduler import get_next_run
    jobs = await asyncio.to_thread(get_all_jobs)
    for job in jobs:
        if job["enabled"]:
            job["next_run_at"] = get_next_run(job["id"]) or job.get("next_run_at")
    return jobs


@app.post("/api/jobs")
async def create_job_endpoint(req: JobCreate):
    from core.task_logger import create_job
    from core.job_scheduler import add_job_to_scheduler
    if len(req.cron.split()) != 5:
        raise HTTPException(status_code=400, detail="cron must be a 5-field expression")
    try:
        job = await asyncio.to_thread(create_job, req.name, req.prompt, req.cron, req.schedule_human)
        await asyncio.to_thread(add_job_to_scheduler, job)
        return job
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail=f"Job '{req.name}' already exists")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/jobs/{job_id}")
async def toggle_job_endpoint(job_id: int, req: JobToggle):
    from core.task_logger import toggle_job
    from core.job_scheduler import pause_job_in_scheduler, resume_job_in_scheduler
    await asyncio.to_thread(toggle_job, job_id, req.enabled)
    if req.enabled:
        await asyncio.to_thread(resume_job_in_scheduler, job_id)
    else:
        await asyncio.to_thread(pause_job_in_scheduler, job_id)
    return {"ok": True}


@app.delete("/api/jobs/{job_id}")
async def delete_job_endpoint(job_id: int):
    from core.task_logger import delete_job
    from core.job_scheduler import remove_job_from_scheduler
    await asyncio.to_thread(remove_job_from_scheduler, job_id)
    await asyncio.to_thread(delete_job, job_id)
    return {"ok": True}


# Serve static files and fallback to index.html
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
