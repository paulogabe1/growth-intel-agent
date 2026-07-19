"""
A custom web search tool using DuckDuckGo, via the `ddgs` package.

Every search tool CrewAI ships with (SerperDevTool,
TavilySearchTool, BraveSearchTool, EXASearchTool) needs its own signup
and API key. DuckDuckGo needs neither, which keeps things consistent
with the rest of this stack (Groq, youtube-transcript-api) which
means fewer accounts and quotas to manage.

Two potential concerns:
  - It's an unofficial library scraping DuckDuckGo's own site, not a
    sanctioned API, so it can break if DuckDuckGo changes something.
    Same category of risk as youtube-transcript-api.
  - DuckDuckGo has no published rate limit, but community reports
    describe bot detection kicking in well before 30 requests per
    minute from one IP. Fine for occasional research queries, not
    something to use in a tight loop.
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
