"""
Tools for creating and deleting scheduled jobs via the desktop agent.
"""
from core.task_logger import create_job, delete_job, get_all_jobs


# Simple cron shorthand parser for common patterns the LLM will produce.
# The agent is expected to call this with a cron string it constructs,
# but we accept a few human aliases too.
_CRON_ALIASES = {
    "daily":    "0 9 * * *",
    "weekdays": "0 9 * * 1-5",
    "weekly":   "0 9 * * 1",
    "hourly":   "0 * * * *",
}


def createJobTool(name: str, prompt: str, cron: str, schedule_human: str) -> str:
    """Creates a recurring scheduled job for L.O.O.M. to run automatically.
    name: short label for this job (e.g. 'Daily Standup').
    prompt: the exact message to send to L.O.O.M. when the job fires (e.g. 'Give me a standup summary').
    cron: standard 5-field cron expression (e.g. '0 10 * * *' for 10am daily, '0 10 * * 1-5' for weekdays).
    schedule_human: human-readable description (e.g. '10:00 AM every weekday').
    Use this when the user asks to schedule or automate a recurring task."""
    resolved_cron = _CRON_ALIASES.get(cron.strip().lower(), cron.strip())
    # Validate cron has 5 fields
    if len(resolved_cron.split()) != 5:
        return f"Invalid cron expression '{cron}'. Use a 5-field cron like '0 10 * * *' (10am daily)."
    try:
        job = create_job(name=name, prompt=prompt, cron=resolved_cron, schedule_human=schedule_human)
        from core.job_scheduler import add_job_to_scheduler
        add_job_to_scheduler(job)
        return f"Scheduled job '{name}' created. It will run {schedule_human} with prompt: \"{prompt}\""
    except Exception as e:
        if "UNIQUE" in str(e):
            return f"A job named '{name}' already exists. Delete it first or use a different name."
        return f"Failed to create job: {e}"


def deleteJobTool(job_name: str) -> str:
    """Deletes a scheduled recurring job by name.
    job_name: the name of the job to delete (exact or partial match).
    Use this when the user asks to cancel, remove, or stop a scheduled job."""
    jobs = get_all_jobs()
    if not jobs:
        return "No scheduled jobs exist."

    query = job_name.lower().strip()
    matches = [j for j in jobs if query in j["name"].lower() or j["name"].lower() in query]
    if not matches:
        known = ", ".join(j["name"] for j in jobs)
        return f"No job matching '{job_name}' found. Known jobs: {known}."

    job = matches[0]
    from core.job_scheduler import remove_job_from_scheduler
    remove_job_from_scheduler(job["id"])
    delete_job(job["id"])
    return f"Scheduled job '{job['name']}' deleted."
