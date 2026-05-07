# autoanime — contributor notes

Python CLI that auto-downloads anime from Nyaa via qBittorrent's Web API.

## Layout

```
src/autoanime/
  cli.py            # Click commands (entry: autoanime.cli:main)
  config.py         # TOML config → ~/.config/autoanime/config.toml
  state.py          # JSON state → ~/.config/autoanime/state.json
  anilist.py        # GraphQL search client (no auth)
  nyaa.py           # RSS fetch + title parsing + ranking + group summaries  ← critical path
  qbittorrent.py    # Web API client (v4/v5 compatible)
  download_plan.py  # Pure planner: which torrents active vs paused
  scheduler.py      # launchd plist generation  ← macOS only
tests/              # ~134 pytest tests, no real HTTP (httpx is mocked at the client level for qbittorrent)
```

Client modules separate HTTP from parsing so parsing is tested with fixture data only. Keep this separation when extending them.

## Critical invariants (don't regress these)

- **`autoanime check --dry-run` must not mutate state.** No `show.downloaded_episodes.add(...)`, no `save_state(shows)`, no qBittorrent calls. The `_record` helper and the trailing `save_state` are both gated on `not dry_run`. There is a regression test (`test_check_dry_run_does_not_mutate_state`).
- **`qbittorrent.add_torrent` must verify the response body, not just status.** qBittorrent's `/api/v2/torrents/add` returns 200 with body `"Ok."` on success and `"Fails."` on failure (duplicate magnet, parse error, etc.). Status-only checks silently mark failures as success and let `check` mark episodes as downloaded that never entered qBittorrent.
- **`group_override` semantics**: when set on a `Show`, `check` (a) bypasses `nyaa.filter` (trusted-uploader filter) for that show and (b) passes `strict_group=group_override` to `rank_entries` so only that group's releases are considered. Both halves are required — bypassing the filter alone lets non-preferred groups in but doesn't pin to one; pinning alone gets filtered out before pinning runs.
- **`add` saves the search query without a group prefix** (`"<title> <quality>"`). The group is stored separately in `group_override`. Earlier versions baked the group into the query, which broke any show whose first-priority group didn't release it.

**Platform scope:** the project is macOS-only today. Only `scheduler.py` and the `~/Library/LaunchAgents/` path in cli.py's `schedule` subcommand are platform-specific — everything else is portable. Cross-platform support should add a new scheduler module per platform (e.g., `scheduler_linux.py` for systemd, `scheduler_windows.py` for Task Scheduler) and dispatch from cli.py based on `sys.platform`. Do not break the macOS path.

## Testing

```bash
uv sync
uv run pytest tests/ -v
```

Tests must pass before committing. Title parsing (`nyaa.parse_title`) is the fragile spot — any edit needs test coverage for every real release-title format it touches. See `tests/test_nyaa.py::TestParseTitle`.

## Dependencies

Keep minimal: `httpx`, `click`, `feedparser`. Don't add pandas, sqlite, async frameworks, or logging libraries. Stdlib `tomllib` handles TOML reads.

## Local install

```bash
# editable install for dev work
uv pip install -e .

# global CLI — clean cache first to avoid stale wheels from previous source state
uv cache clean autoanime
uv tool install . --force
```

## Commit conventions

- Imperative subject lines: `fix list column alignment`, not `Fixed some bugs`
- Body explains why, not what
- **No AI/assistant attribution in commits.** The author is always the repo owner.
- No emoji in commit messages or source code unless explicitly requested
- No `Generated with ...` / `Co-Authored-By: ...` trailers

## Commit and push — required after every change

Every task ends with a commit and push. Don't leave the repo half-done.

```bash
# 1. Run tests
uv run pytest tests/ -v

# 2. Stage specific files (avoid `git add -A` — it picks up stray files)
git add src/autoanime/<file>.py tests/test_<file>.py

# 3. Review the staged diff
git diff --cached

# 4. Commit with HEREDOC for clean formatting
git commit -m "$(cat <<'EOF'
short imperative subject

Optional body explaining the why.
EOF
)"

# 5. Push to main
git push
```

Before pushing, verify:
- Tests green (134+ passed at last count; the number grows over time)
- No secrets in the staged diff (no `.env`, no credentials)
- Commit message has no assistant attribution
- Commit is authored by the repo owner (check with `git log -1 --format=full`)
