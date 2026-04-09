import logging
import json
import re
from google import genai

from core.state import globalState
from agents.desktop_agent.agent import runDesktopAgent
from agents.browser_agent.agent import runBrowserAgent
from core.memory_manager import getImplicitContext

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

client = genai.Client()

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

Respond strictly in json format matching this structure : 
{
    "target_agent": "name_of_agent",
    "plan": "Step 1: ..., Step 2: ...",
    "direct_response": "If target_agent is 'conversational', put your text reply to the user here. Otherwise, leave blank."
}
"""

def processUserRequest(userInput: str, emit=print):
    logging.info("🧠 Orchestrator is thinking deeply...")
    emit("__status__Thinking...")

    implicitContext = getImplicitContext(userInput)

    if implicitContext:
        logging.info(f"Subconscious memory triggered: {implicitContext}")
        augmentedPrompt = f"{implicitContext}\n\nUser Request: {userInput}"
    
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
        response = globalState.activeClient.chat.completions.create(**call_kwargs)

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


        targetAgent = decision.get("target_agent")
        plan = decision.get("plan")
        directResponse = decision.get("direct_response")

        logging.info(f"📋 Plan created: {plan}")
        logging.info(f"🔀 Routing to: {targetAgent}")

        # 5. Route to the specialized agents
        if targetAgent == "desktop_agent":
            emit("__status__Running on desktop...")
            globalState.desktopChat = []  # fresh context per task — orchestrator plan is self-contained
            result = runDesktopAgent(plan, userInput)
            emit(result)

            # CRITICAL: Tell OpenRouter what the Gemini hands just did
            globalState.orchestratorChat.append({
                "role": "user",
                "content": f"SYSTEM UPDATE: The desktop agent completed the task. Result: {result}"
            })

        elif targetAgent == "browser_agent":
            emit("__status__Browsing the web...")
            globalState.browserChat = []
            result = runBrowserAgent(plan, userInput)
            emit(result)

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