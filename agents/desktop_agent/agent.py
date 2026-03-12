import logging
from google.genai import types
from tools.registry import LOOM_TOOLS
from core.state import globalState

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

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
        # CRITICAL: Use the stable 2.0 model for complex multi-tool execution
        globalState.desktopChat = globalState.geminiClient.chats.create(
            model="gemini-2.5-flash", 
            config=config
        )
    return globalState.desktopChat


def runDesktopAgent(plan: str) -> str:
    """Executes the specific desktop related plan"""
    logging.info("🖥️ Desktop Agent Took the control of execution")
    
    chat = getDesktopChat()

    try:
        # Because AFC (Automatic Function Calling) is enabled, the SDK will 
        # automatically pause, run the tools, feed the results back to the AI,
        # and return the final summary right here in one line!
        response = chat.send_message(f"Execute this plan : {plan}")
        
        # Safeguard just in case the AI forgets to speak after executing tools
        if not response.text:
            return "Task executed, but no verbal confirmation was generated."
            
        return response.text
        
    except Exception as e:
        return f"Desktop agent encountered an error : {str(e)}"