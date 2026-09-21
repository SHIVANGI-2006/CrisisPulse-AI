"""
services/tavily_service.py
Reusable wrapper around the Tavily Search API.

Used by the Verification Agent to check whether a submitted crisis report
is corroborated by live, real-world news/web results. This is the ONLY
place in the project that talks to Tavily.
"""

import logging

from config import config

logger = logging.getLogger("crisis_agent.tavily")

try:
    from tavily import TavilyClient
except ImportError:  # pragma: no cover
    TavilyClient = None


class TavilyServiceError(Exception):
    """Raised when Tavily cannot be reached or returns something unusable."""
    pass


class TavilyService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.TAVILY_API_KEY
        self._client = None
        if self.api_key and TavilyClient is not None:
            self._client = TavilyClient(api_key=self.api_key)

    def is_available(self) -> bool:
        """True if a Tavily API key is configured (no network call needed)."""
        return self._client is not None

    def search_crisis(self, query: str, max_results: int = 4) -> dict:
        """
        Runs a live web search and returns:
            { "answer": str, "sources": [{"title","url","content"}, ...] }
        Raises TavilyServiceError on failure.
        """
        if TavilyClient is None:
            raise TavilyServiceError(
                "The 'tavily-python' package is not installed. Run: pip install tavily-python"
            )
        if not self._client:
            raise TavilyServiceError(
                "TAVILY_API_KEY is not configured. Add it to your .env file "
                "(get a free key at https://app.tavily.com)."
            )

        try:
            resp = self._client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=True,
                topic="news",
            )
        except Exception as exc:
            logger.error("Tavily search failed: %s", exc)
            raise TavilyServiceError(f"Tavily API error: {exc}") from exc

        answer = (resp or {}).get("answer", "") or ""
        sources = [
            {
                "title": r.get("title", "Untitled source"),
                "url": r.get("url", ""),
                "content": (r.get("content") or "")[:300],
            }
            for r in (resp or {}).get("results", [])
        ]
        return {"answer": answer, "sources": sources}
