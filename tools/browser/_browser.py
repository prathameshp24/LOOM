from playwright.sync_api import sync_playwright, Page

_pw = None
_browser = None


def get_page() -> Page:
    """Returns a reusable Playwright page. Launches headless Chromium on first call."""
    global _pw, _browser
    if _browser is None or not _browser.is_connected():
        _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(headless=True)
    ctx = _browser.contexts[0] if _browser.contexts else _browser.new_context()
    return ctx.pages[0] if ctx.pages else ctx.new_page()
