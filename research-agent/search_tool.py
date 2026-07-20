"""
Web search via DuckDuckGo (the `ddgs` package), instead of CrewAI's
built-in tools (Serper, Tavily, Brave, EXA), which all need their own
signup and API key. DuckDuckGo needs neither.

Tradeoff: it's an unofficial library scraping DuckDuckGo's site, not a
sanctioned API, so it can break if they change something, and bot
detection reportedly kicks in around 30 requests/minute from one IP.
Fine for occasional queries, not a tight loop.
"""
from ddgs import DDGS
from crewai.tools import BaseTool


class DuckDuckGoSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = (
        "Search the web for current information on a topic or company. "
        "Input should be a specific search query string. Returns a list "
        "of results with titles, short summaries, and source URLs."
    )

    def _run(self, query: str) -> str:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))

        if not results:
            return f"No results found for: {query}"

        formatted = [
            f"- {r.get('title', '(no title)')}: {r.get('body', '')} "
            f"[source: {r.get('href', '')}]"
            for r in results
        ]
        return "\n".join(formatted)
