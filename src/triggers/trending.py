"""Trending topic detector — aggregates from Google Trends, Twitter, Reddit."""
from __future__ import annotations

import asyncio
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class TrendingTopicDetector:
    """Fetches trending topics from multiple sources."""

    async def get_trending_topics(self, country: str = "united_states") -> list[str]:
        """Get top trending topics from all configured sources."""
        results = await asyncio.gather(
            self._get_google_trends(country),
            self._get_reddit_trending(),
            return_exceptions=True,
        )

        topics: list[str] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Trending source failed", error=str(result))
            elif result:
                topics.extend(result)

        # Deduplicate while preserving order
        seen = set()
        unique_topics = []
        for topic in topics:
            if topic.lower() not in seen:
                seen.add(topic.lower())
                unique_topics.append(topic)

        logger.info("Trending topics fetched", count=len(unique_topics))
        return unique_topics[:20]

    async def _get_google_trends(self, country: str) -> list[str]:
        """Fetch trending searches from Google Trends via pytrends."""
        try:
            from pytrends.request import TrendReq
            # Run synchronous pytrends in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._pytrends_fetch, country)
        except ImportError:
            logger.warning("pytrends not installed — skipping Google Trends")
            return []
        except Exception as exc:
            logger.warning("Google Trends fetch failed", error=str(exc))
            return []

    def _pytrends_fetch(self, country: str) -> list[str]:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=360)
        trending_df = pytrends.trending_searches(pn=country)
        return trending_df[0].tolist()[:10]

    async def _get_reddit_trending(self) -> list[str]:
        """Fetch hot topics from Reddit (r/technology, r/business)."""
        try:
            import httpx
            topics = []
            subreddits = ["technology", "business", "marketing"]
            async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "MAMA/0.1"}) as client:
                for sub in subreddits[:2]:
                    response = await client.get(f"https://www.reddit.com/r/{sub}/hot.json?limit=5")
                    if response.status_code == 200:
                        posts = response.json().get("data", {}).get("children", [])
                        topics.extend([p["data"]["title"] for p in posts[:3]])
            return topics
        except Exception as exc:
            logger.warning("Reddit trending fetch failed", error=str(exc))
            return []
