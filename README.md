# autoanime

Auto-download anime episodes from Nyaa via qBittorrent when they air.

## Install

```bash
uv tool install .
```

## Setup

```bash
# Generate default config
autoanime

# Edit ~/.config/autoanime/config.toml with your qBittorrent Web UI settings
```

Requires qBittorrent running with Web UI enabled (Preferences > Web UI).

## Usage

```bash
# Search AniList
autoanime search "Frieren"

# Add a show
autoanime add "Frieren"
autoanime add "One Piece" --from 1120     # skip episodes 1-1119
autoanime add "Dandadan" --group Erai-raws --quality 720p

# See what's tracked
autoanime list

# Check what's available on Nyaa
autoanime status

# Download new episodes
autoanime check              # sends magnets to qBittorrent
autoanime check --dry-run    # preview without downloading
autoanime check --verbose    # detailed matching output

# Remove a show
autoanime remove "Frieren"

# Auto-run every 15 minutes via launchd
autoanime schedule install
autoanime schedule uninstall
```

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

[nyaa]
mirrors = ["nyaa.si", "nyaa.land"]
category = "1_2"
filter = 2
poll_interval_minutes = 15
```

## How it works

1. You add shows via `autoanime add` — resolves titles against AniList
2. `autoanime check` polls Nyaa RSS feeds filtered by your preferred group + quality
3. New episodes are sent to qBittorrent as magnet links via its Web API
4. Episode tracking prevents duplicates; finished shows auto-archive
