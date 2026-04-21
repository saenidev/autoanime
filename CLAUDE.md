# CLAUDE.md

Guidance for Claude agents working on this repo.

## Project

`autoanime` — Python CLI that auto-downloads anime from Nyaa via qBittorrent's Web API. Designed to run every 15 min via macOS `launchd`.

## Layout

```
src/autoanime/
  cli.py          # Click commands (entry point: autoanime.cli:main)
  config.py       # TOML config → ~/.config/autoanime/config.toml
  state.py        # JSON state → ~/.config/autoanime/state.json, Show dataclass, atomic writes
  anilist.py      # GraphQL search (no auth required)
  nyaa.py         # RSS fetch, title parsing, match ranking  ← CRITICAL PATH
  qbittorrent.py  # Web API client
  scheduler.py    # launchd plist generation
tests/            # 75 pytest tests, no HTTP mocking
```

AniList and Nyaa clients deliberately separate parsing from HTTP so the parsing can be tested with fixture data. Keep this separation when extending them.

## Testing

```bash
uv sync
uv run pytest tests/ -v
```

All tests must pass before committing. Title parsing is the fragile part — any change to `nyaa.parse_title` needs test coverage for every real release-title format it touches. See `tests/test_nyaa.py::TestParseTitle`.

## Dependencies

Keep minimal: `httpx`, `click`, `feedparser`. Do not add pandas, sqlite, async frameworks, or logging libraries. Stdlib `tomllib` handles TOML reads.

## Installing locally

```bash
uv pip install -e .     # editable install for development
uv tool install .       # global install, puts `autoanime` on PATH
```

## Commits

**Never add Claude attribution to commits.** No `Generated with Claude Code`, no `Co-Authored-By: Claude`, no mention of AI/Claude in commit messages. The author is `saenidev`.

Write conventional-style subject lines (short, imperative): `fix list command column alignment`, not `Fixed some bugs`.

## Commit and push workflow

```bash
# 1. Run tests
uv run pytest tests/ -v

# 2. Stage specific files (avoid `git add -A` / `git add .`)
git add src/autoanime/nyaa.py tests/test_nyaa.py

# 3. Review what's staged
git diff --cached

# 4. Commit with HEREDOC for clean multi-line formatting
git commit -m "$(cat <<'EOF'
short imperative subject

Optional body explaining why, not what.
EOF
)"

# 5. Push
git push
```

Before pushing:
- Tests green
- No secrets (no `.env`, no credentials) in staged diff
- No Claude attribution in message
- No emoji in code or commit messages unless explicitly requested
