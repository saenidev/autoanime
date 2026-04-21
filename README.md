# autoanime

Auto-download anime episodes from Nyaa via qBittorrent when they air.

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

Installs a `launchd` plist that runs `autoanime check` on the interval set by `poll_interval_minutes` in config.toml (default 60 min).

## Usage

```bash
# Search AniList (read-only)
autoanime search "Frieren"

# Add a show to the watchlist
autoanime add "Frieren"
autoanime add "One Piece" --from 1120         # skip eps 1-1119
autoanime add "Dandadan" --group Erai-raws    # override release group
autoanime add "Show" --quality 720p           # override default quality
autoanime add "Show" --dir ~/Anime/Show       # custom save path

# View tracked shows (air day shown in your local timezone)
autoanime list

# See what's new on Nyaa
autoanime status

# Download new episodes
autoanime check              # live: sends magnets to qBittorrent
autoanime check --dry-run    # preview without downloading
autoanime check --verbose    # show matching decisions

# Remove a show
autoanime remove "Frieren"

# launchd scheduling
autoanime schedule install
autoanime schedule uninstall
```

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
filter = 2                    # Trusted uploaders only
poll_interval_minutes = 60
```

After editing `poll_interval_minutes`, re-run `autoanime schedule install` to apply.

## How it works

1. `autoanime add` resolves titles via AniList (no auth required).
2. `autoanime check` polls the configured Nyaa mirrors via RSS, filtered by group priority + quality + trusted-uploader filter.
3. Title parsing extracts episode number, group, quality, batch flag, and version; ranking picks the best release per episode.
4. Magnets are sent to qBittorrent through its Web API, tagged for per-show state tracking.
5. Finished shows auto-archive once all episodes are downloaded.

## Storage

| Path | Purpose |
|---|---|
| `~/.config/autoanime/config.toml` | User config |
| `~/.config/autoanime/state.json` | Watchlist + per-show episode sets |
| `~/.config/autoanime/autoanime.log` | launchd stdout/stderr |
| `~/Library/LaunchAgents/com.autoanime.check.plist` | Schedule |
