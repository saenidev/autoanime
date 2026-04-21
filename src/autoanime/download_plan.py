"""Plan which torrents to add active vs. paused, and which paused ones to resume.

This module is pure Python — no HTTP, no state mutation — so the decision logic
is fully testable. The CLI layer calls into here with data it has already fetched.
"""

from __future__ import annotations

from dataclasses import dataclass

from autoanime.nyaa import parse_title

ACTIVE_STATES = {
    "downloading",
    "metaDL",
    "stalledDL",
    "queuedDL",
    "allocating",
    "forcedDL",
    "checkingDL",
    "checkingResumeData",
}
PAUSED_STATES = {"pausedDL", "stoppedDL"}


@dataclass
class DownloadPlan:
    to_add_active: list[dict]
    to_add_paused: list[dict]
    to_resume_hashes: list[str]


def _ep_num_from_name(name: str) -> int:
    parsed = parse_title(name)
    return parsed["episode"] or 0


def plan_downloads(
    new_episodes: list[dict],
    existing_torrents: list[dict],
    max_concurrent: int,
) -> DownloadPlan:
    """Decide what to do given current state and new episodes.

    Results are ordered by episode number (earliest first) in every list so the
    caller can apply queue priority / first-piece priority in natural reading
    order.

    max_concurrent <= 0 means unlimited: every new episode goes active, and
    every paused episode gets resumed.
    """
    unlimited = max_concurrent <= 0

    active_count = sum(
        1 for t in existing_torrents if t.get("state") in ACTIVE_STATES
    )
    paused = [t for t in existing_torrents if t.get("state") in PAUSED_STATES]
    paused_sorted = sorted(paused, key=lambda t: _ep_num_from_name(t.get("name", "")))

    if unlimited:
        to_resume = paused_sorted
        effective_active = active_count + len(to_resume)
    else:
        slots = max(0, max_concurrent - active_count)
        to_resume = paused_sorted[:slots]
        effective_active = active_count + len(to_resume)

    new_sorted = sorted(new_episodes, key=lambda e: e.get("episode") or 0)
    to_add_active: list[dict] = []
    to_add_paused: list[dict] = []
    for entry in new_sorted:
        if unlimited or effective_active < max_concurrent:
            to_add_active.append(entry)
            effective_active += 1
        else:
            to_add_paused.append(entry)

    return DownloadPlan(
        to_add_active=to_add_active,
        to_add_paused=to_add_paused,
        to_resume_hashes=[t["hash"] for t in to_resume],
    )
