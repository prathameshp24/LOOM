import logging
import json
import re
from core.state import globalState
from tools.browser.search import web_search
from tools.browser.page import get_page_text, open_url
from tools.browser.automation import click_element, fill_form, take_screenshot
from tools.registry import get_openai_tools

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

BROWSER_TOOLS = [web_search, get_page_text, open_url, click_element, fill_form, take_screenshot]

BROWSER_SYSTEM_PROMPT = """
You are the L.O.O.M. Browser Agent.
Your job is to research and automate tasks on the web.

Guidelines:
- Use web_search first to find relevant URLs before navigating
- Use get_page_text for reading content — it's fast and doesn't need JS
- Use open_url + click_element + fill_form only when interaction is needed
- Use take_screenshot to capture visual confirmation of completed actions
- Be concise in your final response — summarize what you found or did

CRITICAL SEARCH RULES:
- Do NOT repeat similar searches with slightly different wording. One good search is enough.
- After 2 searches maximum, stop searching and synthesize your answer from what you have.
- If you already have enough information to answer, stop calling tools and respond immediately.
- Do not loop — if a search returns results, USE them. Do not search again for the same thing.
"""


def _strip_thinking(text: str) -> str:
    return re.sub(r'<think>.*?</think>', '', text or '', flags=re.DOTALL).strip()


def runBrowserAgent(plan: str, userInput: str = "") -> str:
    """Executes a browser-based research or automation plan."""
    logging.info("🌐 Browser Agent activated")

    if not globalState.browserChat:
        globalState.browserChat.append({"role": "system", "content": BROWSER_SYSTEM_PROMPT})

    globalState.browserChat.append({"role": "user", "content": f"Execute this plan: {plan}"})

    available_tools = get_openai_tools(BROWSER_TOOLS)
    tool_map = {t.__name__: t for t in BROWSER_TOOLS}
    MAX_ITERATIONS = 8

    for iteration in range(MAX_ITERATIONS):
        try:
            extra = {"think": False} if globalState.mode == "local" else {}
            logging.info(f"🌐 [{globalState.mode.upper()}] Browser → {globalState.desktopModel} (iter {iteration + 1}/{MAX_ITERATIONS})")
            response = globalState.activeClient.chat.completions.create(
                model=globalState.desktopModel,
                messages=globalState.browserChat,
                tools=available_tools,
                tool_choice="auto",
                extra_body=extra,
            )
            message = response.choices[0].message
            globalState.browserChat.append(message)

            if not message.tool_calls:
                return _strip_thinking(message.content) or "Browser task completed."

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                logging.info(f"🌐 Browser tool: {name}({args})")

                fn = tool_map.get(name)
                result = fn(**args) if fn else f"Error: tool '{name}' not found"

                # Truncate large tool results to keep context from bloating
                content = str(result)
                if len(content) > 2000:
                    content = content[:2000] + "\n...[truncated]"

                globalState.browserChat.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": content,
                })

        except Exception as e:
            logging.error(f"Browser agent error: {e}")
            return f"Browser agent error: {e}"

    return "Browser agent reached the iteration limit. Partial results may be incomplete."
