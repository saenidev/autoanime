# autoanime — contributor notes

Python CLI that auto-downloads anime from Nyaa via qBittorrent's Web API.

## Layout

```
src/autoanime/
  cli.py            # Click commands (entry: autoanime.cli:main)
  config.py         # TOML config → ~/.config/autoanime/config.toml
  state.py          # JSON state → ~/.config/autoanime/state.json
  anilist.py        # GraphQL search client (no auth)
  nyaa.py           # RSS fetch + title parsing + ranking  ← critical path
  qbittorrent.py    # Web API client (v4/v5 compatible)
  download_plan.py  # Pure planner: which torrents active vs paused
  scheduler.py      # launchd plist generation
tests/              # 102 pytest tests, no HTTP mocking
```

Client modules separate HTTP from parsing so parsing is tested with fixture data only. Keep this separation when extending them.

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
- Tests green (`101+ passed`)
- No secrets in the staged diff (no `.env`, no credentials)
- Commit message has no assistant attribution
- Commit is authored by the repo owner (check with `git log -1 --format=full`)
