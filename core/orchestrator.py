import logging
import json
from google import genai
from google.genai import types

from core.state import globalState
from agents.desktop_agent.agent import runDesktopAgent

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

client = genai.Client()

ORCHESTRATOR_PROMPT = """
You are the master orchestrator for L.O.O.M.
Your job is to analyze the user's request, create a step by step plan and route it to the correct specialized agent.

Currently available agents:
1. "desktop_agent": Handles OS interactions, opening apps, playing music, volume, brightness and timers, searching and reading files, etc.
2. "coding_agent": (OFFLINE)
3. "research_agent": (OFFLINE)
4. "conversational": Use this if the user is just chatting, asking a question that doesn't require physical desktop actions, or asking about past actions.


Respond strictly in json format matching this structure : 
{
    "target_agent": "name_of_agent",
    "plan": "Step 1: ..., Step 2: ...",
    "direct_response": "If target_agent is 'conversational', put your text reply to the user here. Otherwise, leave blank."
}
"""

def processUserRequest(userInput: str):
    print(f"\nYou: {userInput}")
    logging.info("🧠 Orchestrator is thinking deeply...")

    # 1. Initialize memory with the System Prompt if it's empty
    if not globalState.orchestratorChat:
        globalState.orchestratorChat.append({
            "role": "system",
            "content": ORCHESTRATOR_PROMPT
        })

    # 2. Add the user's new prompt to memory
    globalState.orchestratorChat.append({
        "role": "user",
        "content": userInput
    })

    try:
        # 3. Call OpenRouter with Reasoning Enabled
        response = globalState.openrouterClient.chat.completions.create(
            model="openrouter/hunter-alpha",
            messages=globalState.orchestratorChat,
            response_format={"type": "json_object"}, 
            extra_body={"reasoning": {"enabled": True}}
        )

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
        # ---------------------------

        # 4. Parse the JSON Output
        raw_text = ai_message.content.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()

        decision = json.loads(raw_text)
        targetAgent = decision.get("target_agent")
        plan = decision.get("plan")
        directResponse = decision.get("direct_response")

        logging.info(f"📋 Plan created: {plan}")
        logging.info(f"🔀 Routing to: {targetAgent}")

        # 5. Route to the specialized agents
        if targetAgent == "desktop_agent":
            result = runDesktopAgent(plan)
            print(f"\n🧵 (Desktop): {result}\n")
            
            # CRITICAL: Tell OpenRouter what the Gemini hands just did
            globalState.orchestratorChat.append({
                "role": "user", 
                "content": f"SYSTEM UPDATE: The desktop agent completed the task. Result: {result}"
            })
            
        elif targetAgent == "conversational":
            print(f"\n🧵: {directResponse}\n")
            
        else:
            print(f"\n🧵 Orchestrator: I need the {targetAgent} to do this, but it is offline.\n")

    except Exception as e:
        logging.error(f"Orchestrator failed to route the task: {e}")