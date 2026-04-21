from __future__ import annotations

import re
import time
from urllib.parse import quote_plus

import feedparser
import httpx

TRACKERS = [
    "http://nyaa.tracker.wf:7777/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://tracker.torrent.eu.org:451/announce",
]


def parse_title(title: str) -> dict:
    """Extract group, episode, quality, batch flag, and version from a release title."""
    group_match = re.match(r"\[([^\]]+)\]", title)
    group = group_match.group(1) if group_match else None

    episode = None
    se_match = re.search(r"S\d+E(\d+)", title, re.IGNORECASE)
    if se_match:
        episode = int(se_match.group(1))
    else:
        ep_match = re.search(r" - (\d+)", title)
        if ep_match:
            episode = int(ep_match.group(1))

    quality_match = re.search(r"(2160|1080|720|480)p", title)
    quality = f"{quality_match.group(1)}p" if quality_match else None

    is_batch = (
        bool(re.search(r"\(\d+\s*[-~]\s*\d+\)", title))
        or bool(re.search(r"\[\d+\s*[-~]\s*\d+\]", title))
        or bool(re.search(r" - \d+\s*[-~]\s*\d+(?!\d)", title))
        or "batch" in title.lower()
    )

    version_match = re.search(r"v(\d+)", title)
    version = int(version_match.group(1)) if version_match else 1

    return {
        "group": group,
        "episode": episode,
        "quality": quality,
        "is_batch": is_batch,
        "version": version,
    }


def _parse_size(size_str: str) -> int:
    match = re.match(r"([\d.]+)\s*(TiB|GiB|MiB|KiB)", size_str)
    if not match:
        return 0
    value = float(match.group(1))
    unit = match.group(2)
    multipliers = {"KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4}
    return int(value * multipliers.get(unit, 0))


def build_magnet(info_hash: str, title: str) -> str:
    dn = quote_plus(title)
    tracker_params = "&".join(f"tr={quote_plus(t)}" for t in TRACKERS)
    return f"magnet:?xt=urn:btih:{info_hash}&dn={dn}&{tracker_params}"


def fetch_rss(
    query: str,
    mirrors: list[str],
    category: str,
    filter_: int,
    retries: int = 3,
) -> list[dict]:
    for mirror in mirrors:
        for attempt in range(retries):
            try:
                resp = httpx.get(
                    f"https://{mirror}/",
                    params={"page": "rss", "q": query, "c": category, "f": filter_},
                    timeout=15,
                    follow_redirects=True,
                )
                resp.raise_for_status()
                return _parse_feed(resp.text)
            except httpx.HTTPError:
                if attempt < retries - 1:
                    time.sleep(2**attempt)
                continue
    return []


def _parse_feed(xml_text: str) -> list[dict]:
    feed = feedparser.parse(xml_text)
    entries = []
    for entry in feed.entries:
        info_hash = getattr(entry, "nyaa_infohash", "") or ""
        size_str = getattr(entry, "nyaa_size", "0 MiB")
        seeders = int(getattr(entry, "nyaa_seeders", 0) or 0)

        parsed = parse_title(entry.title)

        entries.append(
            {
                "title": entry.title,
                "info_hash": info_hash,
                "magnet": build_magnet(info_hash, entry.title) if info_hash else "",
                "size_bytes": _parse_size(size_str),
                "seeders": seeders,
                **parsed,
            }
        )
    return entries


def rank_entries(
    entries: list[dict],
    group_priority: list[str],
    quality: str,
    max_size_mb: int,
) -> list[dict]:
    max_size_bytes = max_size_mb * 1024 * 1024

    filtered = []
    for e in entries:
        if e["is_batch"]:
            continue
        if e["episode"] is None:
            continue
        if 0 < e["size_bytes"] > max_size_bytes:
            continue
        if e["quality"] and e["quality"] != quality:
            continue
        filtered.append(e)

    def sort_key(e: dict) -> tuple:
        group = e["group"] or ""
        try:
            priority = group_priority.index(group)
        except ValueError:
            priority = len(group_priority)
        return (priority, -e["seeders"])

    filtered.sort(key=sort_key)
    return filtered
