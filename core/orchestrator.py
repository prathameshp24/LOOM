import asyncio
import logging
import json
import re
import time
from google import genai

from core.state import globalState
from agents.desktop_agent.agent import runDesktopAgent
from agents.browser_agent.agent import runBrowserAgent
from core.memory_manager import getImplicitContext
from core.training_logger import log_orchestrator
from core.task_logger import log_task_run

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

client = genai.Client()

_HABIT_KEYWORDS = {
    "habit", "meditat", "workout", "work out", "exercise", "streak",
    "gym", "ran", "yoga", "journal", "log my", "track",
    "did i", "have i", "on track", "sessions", "week streak", "day streak",
}

def _is_habit_related(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _HABIT_KEYWORDS)

_COMPLEX_KEYWORDS = {
    "and then", "after that", "while", "simultaneously", "at the same time",
    "multiple", "both", "schedule", "remind me", "set up", "automate",
    "every", "when i", "if i", "monitor", "track", "compare", "research",
    "find me", "look up", "search for", "browse", "open website", "go to",
}

def _is_complex(text: str) -> bool:
    """True if the query likely needs multi-step reasoning (longer or multi-action)."""
    lower = text.lower()
    if len(lower.split()) > 12:
        return True
    return any(kw in lower for kw in _COMPLEX_KEYWORDS)

def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks emitted by local Qwen3 reasoning."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def _parse_plan_steps(plan: str) -> list[str]:
    """Extract ordered steps from a 'Step 1: ... Step 2: ...' plan string."""
    steps = re.findall(r'Step\s+\d+[:.]\s*(.+?)(?=\s*Step\s+\d+|$)', plan, re.DOTALL | re.IGNORECASE)
    if steps:
        return [s.strip().rstrip(',') for s in steps if s.strip()]
    return [l.strip() for l in plan.split('\n') if l.strip()] or [plan]

ORCHESTRATOR_PROMPT = """
You are the master orchestrator for L.O.O.M.
Your job is to analyze the user's request, create a step by step plan and route it to the correct specialized agent.

Currently available agents:
1. "desktop_agent": Handles OS interactions, opening apps, playing music, volume, brightness and timers, searching and reading files, etc.
2. "browser_agent": Handles web research, searching the internet, reading webpages, filling forms, clicking elements on websites, taking screenshots of browser content.
3. "coding_agent": (OFFLINE)
4. "conversational": Use this if the user is just chatting, asking a question that doesn't require physical desktop actions, or asking about past actions.

CRITICAL MEMORY RULE:
- If the user explicitly asks you to SAVE or REMEMBER a new fact, route to `desktop_agent` to use the `rememberFact` tool.
- If a [SYSTEM MEMORY: ...] block is provided in the user's prompt, use that information to fulfill their request immediately without asking the desktop_agent to search for it!

HABIT RULE:
- If a [SYSTEM HABIT CONTEXT: ...] block is present, use it to answer habit questions conversationally without calling a tool.
- If the user says they completed a habit (meditated, worked out, ran, did DSA, etc.), route to `desktop_agent` with a plan to call `logHabitTool`.
- If the user asks to create or start tracking a new habit, route to `desktop_agent` to call `createHabitTool`.

JOB SCHEDULING RULE:
- If the user asks to schedule, automate, or repeat something on a recurring basis (e.g. "remind me every day at 10am", "schedule a standup", "run X every weekday"), route to `desktop_agent` to call `createJobTool`.
- `createJobTool` requires: name (short label), prompt (exact message to send L.O.O.M. when job fires), cron (5-field cron e.g. "0 10 * * 1-5"), schedule_human (e.g. "10:00 AM every weekday").
- If the user asks to cancel or delete a scheduled job, route to `desktop_agent` to call `deleteJobTool`.

Respond strictly in json format matching this structure : 
{
    "target_agent": "name_of_agent",
    "plan": "Step 1: ..., Step 2: ...",
    "direct_response": "If target_agent is 'conversational', put your text reply to the user here. Otherwise, leave blank."
}
"""

async def processUserRequest(userInput: str, emit=print):
    logging.info("🧠 Orchestrator is thinking deeply...")
    emit("__status__Thinking...")

    implicitContext = await asyncio.to_thread(getImplicitContext, userInput)
    if implicitContext:
        logging.info(f"Subconscious memory triggered: {implicitContext}")

    habitContext = ""
    if _is_habit_related(userInput):
        from core.habit_manager import getHabitContextForOrchestrator
        habitContext = await asyncio.to_thread(getHabitContextForOrchestrator)
        if habitContext:
            logging.info(f"Habit context injected: {habitContext[:80]}...")

    contextParts = [c for c in [implicitContext, habitContext] if c]
    if contextParts:
        augmentedPrompt = "\n".join(contextParts) + f"\n\nUser Request: {userInput}"
    else:
        augmentedPrompt = userInput

    # 1. Initialize memory with the System Prompt if it's empty
    if not globalState.orchestratorChat:
        globalState.orchestratorChat.append({
            "role": "system",
            "content": ORCHESTRATOR_PROMPT
        })

    # 2. Add the user's new prompt to memory
    globalState.orchestratorChat.append({
        "role": "user",
        "content": augmentedPrompt
    })

    try:
        # 3. Call active backend (cloud or local)
        call_kwargs = dict(
            model=globalState.orchestratorModel,
            messages=globalState.orchestratorChat,
            response_format={"type": "json_object"},
        )
        if globalState.mode == "cloud":
            use_reasoning = _is_complex(userInput)
            call_kwargs["extra_body"] = {"reasoning": {"enabled": use_reasoning}}
            logging.info("🧠 Complex query — reasoning enabled" if use_reasoning else "⚡ Simple query — reasoning skipped")
        else:
            call_kwargs["extra_body"] = {"think": False}

        logging.info(f"🌐 [{globalState.mode.upper()}] Orchestrator → {globalState.orchestratorModel}")
        _t0 = time.monotonic()
        response = await asyncio.to_thread(
            globalState.activeClient.chat.completions.create, **call_kwargs
        )

        if getattr(response, 'choices', None) is None or not response.choices:
            logging.error("OpenRouter API Glitch: Returned null/empty choices. Model overloaded.")
            emit("My API connection just glitched. Try again!")
            return
        


        ai_message = response.choices[0].message
        
        # --- MEMORY PRESERVATION ---
        assistant_memory = {
            "role": "assistant",
            "content": ai_message.content
        }

        

        # Keep reasoning details so the model remembers HOW it thought
        if hasattr(ai_message, 'reasoning_details') and ai_message.reasoning_details:
            assistant_memory["reasoning_details"] = ai_message.reasoning_details
            
        globalState.orchestratorChat.append(assistant_memory)
        # Trim: keep system prompt + last 20 messages to prevent token bloat
        if len(globalState.orchestratorChat) > 21:
            globalState.orchestratorChat = globalState.orchestratorChat[:1] + globalState.orchestratorChat[-20:]
        # ---------------------------

        # 4. Parse the JSON Output (strip Qwen3 <think> blocks first)
        raw_text = _strip_thinking(ai_message.content or "{}")
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()

        try:
            decision = json.loads(raw_text)
        except json.JSONDecodeError:
            decision = {}

        if not decision:
            logging.error("Model returned invalid empty JSON.")
            emit("I lost my train of thought. Can you rephrase that?")
            return

        _latency_ms = int((time.monotonic() - _t0) * 1000)
        log_orchestrator(
            user_input=userInput,
            memory_context=implicitContext,
            habit_context=habitContext,
            decision=decision,
            latency_ms=_latency_ms,
            model=globalState.orchestratorModel,
            mode=globalState.mode,
        )

        targetAgent = decision.get("target_agent")
        plan = decision.get("plan")
        directResponse = decision.get("direct_response")

        logging.info(f"📋 Plan created: {plan}")
        logging.info(f"🔀 Routing to: {targetAgent}")

        # 5. Route to the specialized agents
        _task_tool_calls: list[dict] = []

        def _tracking_emit(msg: str):
            """Wraps emit to capture tool calls for task run logging."""
            if msg.startswith("__dag__"):
                try:
                    data = json.loads(msg[len("__dag__"):])
                    if data.get("type") == "tool":
                        _task_tool_calls.append({"name": data["name"], "result": data.get("result", "")})
                except Exception:
                    pass
            emit(msg)

        _t_route = time.monotonic()

        if targetAgent == "desktop_agent":
            emit("__status__Running on desktop...")
            steps = _parse_plan_steps(plan) if plan else []
            if steps:
                emit(f"__dag__{json.dumps({'type': 'init', 'steps': steps, 'agent': targetAgent})}")
            globalState.desktopChat = []  # fresh context per task — orchestrator plan is self-contained
            result = await runDesktopAgent(plan, userInput, emit=_tracking_emit)
            emit(result)
            log_task_run(userInput, "desktop_agent", plan or "", _task_tool_calls, result,
                         duration_ms=int((time.monotonic() - _t_route) * 1000))

            # CRITICAL: Tell OpenRouter what the Gemini hands just did
            globalState.orchestratorChat.append({
                "role": "user",
                "content": f"SYSTEM UPDATE: The desktop agent completed the task. Result: {result}"
            })

        elif targetAgent == "browser_agent":
            emit("__status__Browsing the web...")
            steps = _parse_plan_steps(plan) if plan else []
            if steps:
                emit(f"__dag__{json.dumps({'type': 'init', 'steps': steps, 'agent': targetAgent})}")
            globalState.browserChat = []
            result = await runBrowserAgent(plan, userInput, emit=_tracking_emit)
            emit(result)
            log_task_run(userInput, "browser_agent", plan or "", _task_tool_calls, result,
                         duration_ms=int((time.monotonic() - _t_route) * 1000))

            globalState.orchestratorChat.append({
                "role": "user",
                "content": f"SYSTEM UPDATE: Browser agent completed the task. Result: {result}"
            })

        elif targetAgent == "conversational":
            emit(directResponse)

        else:
            emit(f"I need the {targetAgent} to do this, but it is offline.")

    except Exception as e:
        logging.error(f"Orchestrator failed to route the task: {e}")