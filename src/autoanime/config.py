from __future__ import annotations

import dataclasses
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
# 0 = unlimited (all new episodes download concurrently with priority hint)
# Set to a positive N to pause episodes beyond the Nth per show.
max_concurrent_per_show = 0

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
    # 0 or negative = unlimited (default). Set to N to actually pause downloads
    # beyond the Nth per show (useful if you want strict serial).
    max_concurrent_per_show: int = 0


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


def _only_known(cls, data: dict) -> dict:
    valid = {f.name for f in dataclasses.fields(cls)}
    return {k: v for k, v in data.items() if k in valid}


def load_config(path: Path | None = None) -> Config:
    p = path or CONFIG_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"No config found at {p}. Run `autoanime` to generate defaults."
        )

    with open(p, "rb") as f:
        data = tomllib.load(f)

    return Config(
        qbittorrent=QBittorrentConfig(**_only_known(QBittorrentConfig, data.get("qbittorrent", {}))),
        defaults=DefaultsConfig(**_only_known(DefaultsConfig, data.get("defaults", {}))),
        nyaa=NyaaConfig(**_only_known(NyaaConfig, data.get("nyaa", {}))),
    )


def generate_default_config(path: Path | None = None) -> Path:
    p = path or CONFIG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(DEFAULT_CONFIG)
    return p
