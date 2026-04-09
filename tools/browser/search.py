try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS


def web_search(query: str, num_results: int = 5) -> str:
    """Search the web using DuckDuckGo. Returns top results with title, URL, and snippet."""
    try:
        results = list(DDGS().text(query, max_results=num_results))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}\n   URL: {r['href']}\n   {r['body']}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"
