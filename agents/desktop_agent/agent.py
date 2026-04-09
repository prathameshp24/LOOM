import logging
import re
from tools.registry import get_openai_tools, get_tools_for_plan, getToolByName
from core.state import globalState
import json
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def _strip_thinking(text: str) -> str:
    return re.sub(r'<think>.*?</think>', '', text or '', flags=re.DOTALL).strip()

DESKTOP_SYSTEM_PROMPT = """
You are the L.O.O.M. Desktop Execution Agent.
You run on Fedora Linux Wayland
Your ONLY job is to take the execution plan provided by the Orchestrator
and use your native tools to execute it flawlessly.
Do not make up tools. If a tool fails, report it.
"""




def runDesktopAgent(plan: str, userInput: str = "") -> str:
    """Executes the specific desktop related plan"""
    logging.info("🖥️ Desktop Agent Took the control of execution")

    if not globalState.desktopChat:
        globalState.desktopChat.append({"role": "system", "content": DESKTOP_SYSTEM_PROMPT})

    globalState.desktopChat.append({"role": "user", "content": f"Execute this plan: {plan}"})

    # In local mode: give the model only the tools it needs (dramatically fewer tokens).
    # In cloud mode: pass all tools (capable models handle the full list fine).
    if globalState.mode == "local":
        focused = get_tools_for_plan(plan, userInput)
        availableTools = get_openai_tools(focused)
    else:
        availableTools = get_openai_tools()
    

    MAX_ITERATIONS = 10
    for _iteration in range(MAX_ITERATIONS):
        try:
            logging.info(f"🖥️ [{globalState.mode.upper()}] Desktop → {globalState.desktopModel}")
            extra = {"think": False} if globalState.mode == "local" else {}
            response = globalState.activeClient.chat.completions.create(
                model=globalState.desktopModel,
                messages=globalState.desktopChat,
                tools=availableTools,
                tool_choice="auto",
                extra_body=extra,
            )

            message = response.choices[0].message

            globalState.desktopChat.append(message)

            if not message.tool_calls:
                return _strip_thinking(message.content) or "Task completed silently"
            
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

    return "Desktop agent reached the iteration limit."