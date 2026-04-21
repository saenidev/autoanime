from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "autoanime"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = """\
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
"""


@dataclass
class QBittorrentConfig:
    host: str = "localhost"
    port: int = 8080
    username: str = "admin"
    password: str = "adminadmin"


@dataclass
class DefaultsConfig:
    quality: str = "1080p"
    group_priority: list[str] = field(
        default_factory=lambda: ["SubsPlease", "Erai-raws", "Judas"]
    )
    max_torrent_size_mb: int = 4000


@dataclass
class NyaaConfig:
    mirrors: list[str] = field(default_factory=lambda: ["nyaa.si", "nyaa.land"])
    category: str = "1_2"
    filter: int = 2
    poll_interval_minutes: int = 15


@dataclass
class Config:
    qbittorrent: QBittorrentConfig = field(default_factory=QBittorrentConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    nyaa: NyaaConfig = field(default_factory=NyaaConfig)


def load_config(path: Path | None = None) -> Config:
    p = path or CONFIG_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"No config found at {p}. Run `autoanime` to generate defaults."
        )

    with open(p, "rb") as f:
        data = tomllib.load(f)

    return Config(
        qbittorrent=QBittorrentConfig(**data.get("qbittorrent", {})),
        defaults=DefaultsConfig(**data.get("defaults", {})),
        nyaa=NyaaConfig(**data.get("nyaa", {})),
    )


def generate_default_config(path: Path | None = None) -> Path:
    p = path or CONFIG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(DEFAULT_CONFIG)
    return p
