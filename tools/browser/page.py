import requests
from bs4 import BeautifulSoup
from tools.browser._browser import get_page


def get_page_text(url: str) -> str:
    """Fetch a webpage and return clean readable text (max 3000 chars). Fast — no JS execution."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = " ".join(text.split())
        return text[:3000] + ("..." if len(text) > 3000 else "")
    except Exception as e:
        return f"Error fetching page: {e}"


def open_url(url: str) -> str:
    """Navigate the browser to a URL using Playwright. Returns page title and current URL."""
    try:
        page = get_page()
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return f"Navigated to: {page.title()} — {page.url}"
    except Exception as e:
        return f"Navigation error: {e}"
