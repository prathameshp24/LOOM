import os
from datetime import datetime
from tools.browser._browser import get_page

SCREENSHOT_DIR = os.path.expanduser("~/Pictures/loom_screenshots")


def click_element(selector: str) -> str:
    """Click an element on the current browser page using a CSS selector."""
    try:
        page = get_page()
        page.click(selector, timeout=5000)
        return f"Clicked: {selector}"
    except Exception as e:
        return f"Click error: {e}"


def fill_form(selector: str, text: str) -> str:
    """Type text into a form field on the current page, identified by a CSS selector."""
    try:
        page = get_page()
        page.fill(selector, text)
        return f"Filled '{selector}' with text"
    except Exception as e:
        return f"Fill error: {e}"


def take_screenshot(filename: str = "") -> str:
    """Take a screenshot of the current browser page and save it. Returns the file path."""
    try:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        if not filename:
            filename = f"loom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.join(SCREENSHOT_DIR, filename)
        get_page().screenshot(path=path)
        return f"Screenshot saved: {path}"
    except Exception as e:
        return f"Screenshot error: {e}"
