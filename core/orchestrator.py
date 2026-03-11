import logging
import json
from google import genai
from google.genai import types

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


Respond strictly in json format matching this structure : 
{
    "target_agent": "name_of_agent",
    "plan": "Step 1: ..., Step 2: ..."
}
"""

def processUserRequest(userInput: str):
    """The main entry point. Plans and routes."""
    print(f"\nYou: {userInput}")
    logging.info("Orchestrator is analyzing the request...")


    config = types.GenerateContentConfig(
        system_instruction=ORCHESTRATOR_PROMPT,
        response_mime_type="application/json",
        temperature=0.1
    )


    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=userInput,
            config=config
        )

        decision = json.loads(response.text)
        targetAgent = decision.get("target_agent")
        plan = decision.get("plan")



        logging.info(f"Plan created : {plan}")
        logging.info(f"Routing to : {targetAgent}")

        if targetAgent == "desktop_agent":
            result = runDesktopAgent(plan)
            print(f"\n🧵 (Desktop): {result}\n")
        
        else:
            print(f"\n🧵 Orchestrator : I need the {targetAgent} to do this, but it is completely offline.\n")


    except Exception as e:
        logging.error(f"Orchestrator failed to route the task. {e}")
    

if __name__ == "__main__":
    print("Initializing L.O.O.M. Multi Agent System")
    testPrompt = "Lower my brightness by 20%, decreae volume by 10%, play namami shamishan"
    processUserRequest(testPrompt)
