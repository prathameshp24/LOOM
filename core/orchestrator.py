import logging
import json
from google import genai
from google.genai import types

from core.state import globalState
from agents.desktop_agent.agent import runDesktopAgent
from core.memory_manager import getImplicitContext

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

def processUserRequest(userInput: str):
    print(f"\nYou: {userInput}")
    logging.info("🧠 Orchestrator is thinking deeply...")

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
        # 3. Call OpenRouter with Reasoning Enabled
        response = globalState.openrouterClient.chat.completions.create(
            model="openrouter/hunter-alpha",
            messages=globalState.orchestratorChat,
            response_format={"type": "json_object"}, 
            extra_body={"reasoning": {"enabled": True}}
        )

        if getattr(response, 'choices', None) is None or not response.choices:
            logging.error("OpenRouter API Glitch: Returned null/empty choices. Model overloaded.")
            print("\n🧵 Orchestrator: My API connection just glitched. Let me catch my breath and try again!\n")
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
        # ---------------------------

        # 4. Parse the JSON Output
        raw_text = ai_message.content or "{}"
        raw_text = raw_text.strip()
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
            print("\n🧵 Orchestrator: I lost my train of thought. Can you rephrase that?\n")
            return


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