import logging
from google import genai
from google.genai import types
from tools.registry import LOOM_TOOLS, getToolByName
from core.state import globalState


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

client = genai.Client()

DESKTOP_SYSTEM_PROMPT = """
You are the L.O.O.M. Desktop Execution Agent.
You run on Fedora Linux Wayland
Your ONLY job is to take the execution plan provided by the Orchestrator
and use your native tools to execute it flawlessly.
Do not make up tools. If a tool fails, report it.
"""

def getDesktopChat():
    """Fetches or initializes the persistent Desktop Agent chat session."""
    if globalState.desktopChat is None:
        config = types.GenerateContentConfig(
            system_instruction=DESKTOP_SYSTEM_PROMPT,
            tools=LOOM_TOOLS,
            temperature=0.0,
        )
        globalState.desktopChat = globalState.client.chats.create(
            model="gemini-2.5-flash", 
            config=config
        )
    return globalState.desktopChat




def runDesktopAgent(plan: str) -> str:
    """Executes the specific desktop related plan"""
    logging.info("Desktop Agent Took the control of execution")

    
    chat = getDesktopChat()


    try:
        response = chat.send_message(f"Execute this plan : {plan}")

        if response.function_calls:
            toolResponses = []
            for functionCall in response.function_calls:
                toolName = functionCall.name
                args = functionCall.args

                logging.info(f"Executing : {toolName}({args})")
                targetFunction = getToolByName(toolName)

                if targetFunction:
                    try:
                        result = targetFunction(**args)
                        toolResponses.append(
                            types.Part.from_function_response(
                                name=toolName, response={"result": result}
                            )
                        )
                    
                    except Exception as e:
                        toolResponses.append(
                            types.Part.from_function_response(
                                name=toolName, response={"error": str(e)}
                            )
                        )
                    
            finalResponse = chat.send_message(toolResponses)
            return finalResponse.text
        
        else:
            return response.text
        
    except Exception as e:
        return f"Desktop agent encountered an error : {str(e)}"
    




