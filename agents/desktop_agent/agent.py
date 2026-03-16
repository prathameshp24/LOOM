import logging
from google.genai import types
from tools.registry import get_openai_tools, getToolByName
from core.state import globalState
import json
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

DESKTOP_SYSTEM_PROMPT = """
You are the L.O.O.M. Desktop Execution Agent.
You run on Fedora Linux Wayland
Your ONLY job is to take the execution plan provided by the Orchestrator
and use your native tools to execute it flawlessly.
Do not make up tools. If a tool fails, report it.
"""




def runDesktopAgent(plan: str) -> str:
    """Executes the specific desktop related plan"""
    logging.info("🖥️ Desktop Agent Took the control of execution")


    if not globalState.desktopChat:
        globalState.desktopChat.append({"role": "system", "content": DESKTOP_SYSTEM_PROMPT})

    globalState.desktopChat.append({"role": "user", "content": f"Execute this plan: {plan}"})

    availableTools = get_openai_tools()
    

    while True:
        try:
            response = globalState.openrouterClient.chat.completions.create(
                model="nvidia/nemotron-3-nano-30b-a3b:free",
                messages=globalState.desktopChat,
                tools=availableTools,
                tool_choice="auto"
            )

            message = response.choices[0].message

            globalState.desktopChat.append(message)

            if not message.tool_calls:
                return message.content or "Task completed silently"
            
            for toolCall in message.tool_calls:
                toolName = toolCall.function.name

                try:
                    arguments = json.loads(toolCall.function.arguments)

                except json.JSONDecodeError:
                    arguments = {}

                logging.info(f"Executing : {toolName}({arguments})")

                targetFunction = getToolByName(toolName)

                if targetFunction:
                    try:
                        result = targetFunction(**arguments)
                        toolResult = str(result)

                    except Exception as e:
                        toolResult = f"Error executing tool : {e}"
                
                else:
                    toolResult = f"Error: {toolName} not found"

                globalState.desktopChat.append({
                    "role": "tool",
                    "tool_call_id": toolCall.id,
                    "name": toolName,
                    "content": toolResult
                })
            
            # The loop goes back to the top to send the results to the AI!
            
        except Exception as e:
            logging.error(f"Desktop agent error: {str(e)}")
            return f"Desktop agent encountered an error: {str(e)}"