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
1. "desktop_agent": Handles OS interactions, opening apps, playing music, volume, brightness and timers, etc.
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


def getOrchestratorChat():
    """Fetches or initializes the persistent Orchestrator chat session."""
    if globalState.orchestratorChat is None:
        config = types.GenerateContentConfig(
        system_instruction=ORCHESTRATOR_PROMPT,
        response_mime_type="application/json",
        temperature=0.1
    )
    
        globalState.orchestratorChat = globalState.client.chats.create(
            model="gemini-2.5-flash",
            config=config
        )

    return globalState.orchestratorChat
        

def processUserRequest(userInput: str):
    """The main entry point. Plans and routes."""
    print(f"\nYou: {userInput}")
    logging.info("Orchestrator is analyzing the request...")


    chat = getOrchestratorChat()
    

    try:
        response = chat.send_message(userInput)

        decision = json.loads(response.text)
        targetAgent = decision.get("target_agent")
        plan = decision.get("plan")
        directResponse = decision.get("direct_response")


        logging.info(f"Plan created : {plan}")
        logging.info(f"Routing to : {targetAgent}")

        if targetAgent == "desktop_agent":
            result = runDesktopAgent(plan)
            print(f"\n🧵 (Desktop): {result}\n")
            chat.send_message(f"SYSTEM UPDATE: The desktop agent completed the task. Result : {result}")
        
        elif targetAgent == "conversational":
            print(f"\n🧵: {directResponse}\n")
        

        else:
            print(f"\n🧵 Orchestrator : I need the {targetAgent} to do this, but it is completely offline.\n")


    except Exception as e:
        logging.error(f"Orchestrator failed to route the task. {e}")
    

# if __name__ == "__main__":
#     print("Initializing L.O.O.M. Multi Agent System")
#     testPrompt = "Lower my brightness by 20%, decreae volume by 10%, play namami shamishan"
#     processUserRequest(testPrompt)
