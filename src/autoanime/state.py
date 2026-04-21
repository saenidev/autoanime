from __future__ import annotations

import dataclasses
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path.home() / ".config" / "autoanime" / "state.json"


@dataclass
class Show:
    anilist_id: int
    title: str
    alt_titles: list[str] = field(default_factory=list)
    search_query: str = ""
    group_override: str | None = None
    quality_override: str | None = None
    download_dir: str | None = None
    total_episodes: int | None = None
    airing_status: str = "UNKNOWN"
    air_day: str | None = None
    downloaded_episodes: set[int] = field(default_factory=set)
    nyaa_fingerprint: str | None = None
    added_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    archived: bool = False


def _show_to_dict(show: Show) -> dict:
    d = asdict(show)
    d["downloaded_episodes"] = sorted(show.downloaded_episodes)
    return d


def _show_from_dict(d: dict) -> Show:
    d = d.copy()
    d["downloaded_episodes"] = set(d.get("downloaded_episodes", []))
    valid = {f.name for f in dataclasses.fields(Show)}
    return Show(**{k: v for k, v in d.items() if k in valid})


def load_state(path: Path | None = None) -> dict[str, Show]:
    p = path or STATE_PATH
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {k: _show_from_dict(v) for k, v in data.get("shows", {}).items()}


def save_state(shows: dict[str, Show], path: Path | None = None) -> None:
    p = path or STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"shows": {k: _show_to_dict(v) for k, v in shows.items()}}
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(p)


def make_slug(title: str) -> str:
    import re

    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug).strip("-")
    return slug
