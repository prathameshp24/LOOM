"""
Training data logger for LOOM's fine-tuning pipeline.

Writes JSONL to loom_db/training_logs/. Each session gets its own file
(date-stamped) so logs are easy to inspect and merge later.

Disk cost: ~600 bytes/orchestrator entry, ~2KB/desktop entry.
At 10 conversations/day → ~700KB/month → 3 months ≈ 2MB total.
"""

import json
import logging
import os
from datetime import datetime, date

LOGS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "loom_db", "training_logs")
)
os.makedirs(LOGS_DIR, exist_ok=True)

# Disable this logger during sensitive sessions via env var:
# LOOM_NO_LOG=1 uvicorn ...
_ENABLED = os.environ.get("LOOM_NO_LOG", "").strip() not in ("1", "true", "yes")


def _log_path(log_type: str) -> str:
    today = date.today().isoformat()
    return os.path.join(LOGS_DIR, f"{log_type}_{today}.jsonl")


def _append(log_type: str, entry: dict):
    if not _ENABLED:
        return
    try:
        entry["ts"] = datetime.utcnow().isoformat()
        entry["type"] = log_type
        with open(_log_path(log_type), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logging.warning(f"Training logger failed (non-fatal): {e}")


def log_orchestrator(
    user_input: str,
    memory_context: str,
    habit_context: str,
    decision: dict,
    latency_ms: int,
    model: str,
    mode: str,
):
    """Log one orchestrator routing decision."""
    _append("orchestrator", {
        "input": user_input[:500],           # cap at 500 chars
        "memory_context": memory_context[:300] if memory_context else "",
        "habit_context": habit_context[:300] if habit_context else "",
        "output": {
            "target_agent": decision.get("target_agent", ""),
            "plan": decision.get("plan", "")[:400],
            "direct_response": decision.get("direct_response", "")[:400],
        },
        "latency_ms": latency_ms,
        "model": model,
        "mode": mode,
    })


def log_desktop(
    plan: str,
    tool_calls: list[dict],
    final_result: str,
    latency_ms: int,
    model: str,
    mode: str,
):
    """Log one desktop agent execution (plan → tool call sequence → result)."""
    # Truncate tool results to keep entries small; full results aren't needed for training
    cleaned_calls = []
    for tc in tool_calls:
        cleaned_calls.append({
            "name": tc.get("name", ""),
            "args": tc.get("args", {}),
            "result": str(tc.get("result", ""))[:300],
        })

    _append("desktop_agent", {
        "plan": plan[:400],
        "tool_calls": cleaned_calls,
        "final_result": final_result[:400],
        "latency_ms": latency_ms,
        "model": model,
        "mode": mode,
    })
