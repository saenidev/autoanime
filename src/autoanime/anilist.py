from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, tzinfo

import httpx

ANILIST_URL = "https://graphql.anilist.co"

SEARCH_QUERY = """
query ($search: String) {
  Page(page: 1, perPage: 5) {
    media(search: $search, type: ANIME) {
      id
      title {
        romaji
        english
        native
      }
      synonyms
      episodes
      status
      nextAiringEpisode {
        airingAt
        episode
      }
    }
  }
}
"""


@dataclass
class AniListResult:
    id: int
    title_romaji: str
    title_english: str | None
    title_native: str | None
    synonyms: list[str]
    episodes: int | None
    status: str
    next_airing_at: int | None
    next_episode: int | None


def search_anime(query: str) -> list[AniListResult]:
    resp = httpx.post(
        ANILIST_URL,
        json={"query": SEARCH_QUERY, "variables": {"search": query}},
        timeout=10,
    )
    resp.raise_for_status()
    return _parse_search_response(resp.json())


def _parse_search_response(data: dict) -> list[AniListResult]:
    results = []
    for media in data.get("data", {}).get("Page", {}).get("media", []):
        nae = media.get("nextAiringEpisode") or {}
        results.append(
            AniListResult(
                id=media["id"],
                title_romaji=media["title"]["romaji"],
                title_english=media["title"].get("english"),
                title_native=media["title"].get("native"),
                synonyms=media.get("synonyms", []),
                episodes=media.get("episodes"),
                status=media["status"],
                next_airing_at=nae.get("airingAt"),
                next_episode=nae.get("episode"),
            )
        )
    return results


def get_air_day(airing_at: int | None, tz: tzinfo | None = None) -> str | None:
    """Return the weekday for an AniList airing timestamp.

    Uses the system's local timezone unless `tz` is provided (mainly for tests).
    """
    if not airing_at:
        return None
    if tz is None:
        dt = datetime.fromtimestamp(airing_at)
    else:
        dt = datetime.fromtimestamp(airing_at, tz=tz)
    return dt.strftime("%A")
