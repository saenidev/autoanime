# autoanime

Auto-download anime episodes from Nyaa via qBittorrent when they air.

> **macOS only for now.** The scheduling layer is `launchd`-based (`~/Library/LaunchAgents/`) and the install helpers shell out to `launchctl`. Everything else (AniList client, Nyaa RSS, title parsing, qBittorrent API) is cross-platform — Linux/Windows support just needs a platform-specific scheduler (systemd timer / Task Scheduler). PRs welcome.

## Install

```bash
uv tool install .
```

Puts `autoanime` on your `PATH`.

## Setup

**1. Generate the config file:**

```bash
autoanime
```

Creates `~/.config/autoanime/config.toml` with sensible defaults.

**2. Enable qBittorrent's Web UI** (Preferences → Web UI):

- Tick "Web User Interface (Remote control)"
- Port: `8080`
- Username / password: `admin` / `adminadmin` (or set your own in both qBittorrent *and* `config.toml`)
- Tick "Bypass authentication for clients on localhost" for hassle-free local use

**3. Install the scheduled check:**

```bash
autoanime schedule install
```

Installs a `launchd` plist that runs `autoanime check` on the interval set by `poll_interval_minutes` in config.toml (default 15 min).

## Usage

```bash
# Search AniList (read-only)
autoanime search "Frieren"

# Add a show to the watchlist (interactive: confirms AniList match, then
# shows a release-group picker sorted by total seeders)
autoanime add "Frieren"
autoanime add "One Piece" --from 1120         # skip eps 1-1119
autoanime add "Dandadan" --group Erai-raws    # skip the picker, force this group
autoanime add "Show" --quality 720p           # override default quality
autoanime add "Show" --dir ~/Anime/Show       # custom save path

# View tracked shows (air day shown in your local timezone)
autoanime list

# See what's new on Nyaa
autoanime status

# Download new episodes
autoanime check              # live: sends magnets to qBittorrent
autoanime check --dry-run    # preview without touching state or qBittorrent
autoanime check --verbose    # show matching decisions

# Remove a show
autoanime remove "Frieren"

# launchd scheduling
autoanime schedule install
autoanime schedule uninstall
```

## Picking a release group

When `add` is invoked without `--group`, it queries Nyaa for the show (unfiltered, regardless of `nyaa.filter`), groups the results by release group, and prompts you to pick one:

```
Available release groups:
  1. Sokudo      5 eps, 312 seeders, latest E05, ~1400MB, 1080p, AV1, dual-audio
  2. ToonsHub    5 eps, 178 seeders, latest E05, ~2100MB, 1080p, HEVC, dual-audio  [preferred]
  3. DKB         5 eps,  94 seeders, latest E05, ~800MB,  1080p, HEVC, dual-audio

Pick a group (1-3) [1]:
```

Sorted by total seeders descending. Tiebreakers: episode count → latest episode → `[preferred]` (groups in your `defaults.group_priority`). The chosen group is saved as `group_override` on the show; subsequent `check` runs only download from that group, and bypass the trusted-uploader filter for that show (so non-trusted groups like Sokudo or DKB still work).

If Nyaa has zero hits at add time (show hasn't aired yet), the picker is skipped and `group_override` stays unset; `check` will fall back to ranking via `defaults.group_priority` once releases appear.

## How batch downloads behave

When several new episodes drop at once (e.g. you added a show mid-season, or missed a few checks), autoanime adds them all to qBittorrent concurrently and tells qBittorrent to sort them in the queue by episode number — **lowest new episode at the top**. "Lowest" is relative to what you haven't downloaded yet: if you already have eps 1–10 and eps 11–14 arrive, ep 11 goes on top.

**Honest caveat:** qBittorrent doesn't do bandwidth prioritization *between* active torrents — with N parallel downloads splitting your link, they finish at roughly the same time regardless of queue position. Queue priority only affects bandwidth when qBittorrent's queueing system is enabled (Preferences → BitTorrent → "Torrent queueing") with a limited `max_active_downloads`.

If you want strict serial (the lowest-numbered new episode finishes before the next one starts), set `max_concurrent_per_show = 1` in config.toml. Episodes beyond the limit are added to qBittorrent paused and tagged `autoanime-<show-slug>`; subsequent `check` runs resume the earliest paused episode when a slot frees up.

## Config

`~/.config/autoanime/config.toml`:

```toml
[qbittorrent]
host = "localhost"
port = 8080
username = "admin"
password = "adminadmin"

[defaults]
quality = "1080p"
group_priority = ["SubsPlease", "Erai-raws", "Judas"]
max_torrent_size_mb = 4000
max_concurrent_per_show = 0    # 0 = unlimited concurrent; set N for strict serial

[nyaa]
mirrors = ["nyaa.si", "nyaa.land"]
category = "1_2"             # Anime - English-translated
filter = 2                    # Trusted uploaders only (per-show group_override bypasses this)
poll_interval_minutes = 15
```

After editing `poll_interval_minutes`, re-run `autoanime schedule install` to apply.

## How it works

1. `autoanime add` resolves titles via AniList (no auth), then queries Nyaa for the show, summarises hits per release group, and prompts for one. The chosen group is saved as `group_override` on the show.
2. `autoanime check` polls the configured Nyaa mirrors via RSS. For shows with `group_override` set, the trusted-uploader filter is bypassed and ranking is locked to that group; otherwise `defaults.group_priority` and `nyaa.filter` apply.
3. Title parsing extracts episode number, group, quality, batch flag, and version; ranking picks the best release per episode.
4. Magnets are sent to qBittorrent through its Web API, tagged `autoanime` and `autoanime-<slug>` for per-show state tracking.
5. `--dry-run` is a true preview — no state mutations, no qBittorrent calls.
6. Finished shows auto-archive once all episodes are downloaded.

## Storage

| Path | Purpose |
|---|---|
| `~/.config/autoanime/config.toml` | User config |
| `~/.config/autoanime/state.json` | Watchlist + per-show episode sets |
| `~/.config/autoanime/autoanime.log` | launchd stdout/stderr |
| `~/Library/LaunchAgents/com.autoanime.check.plist` | Schedule |
