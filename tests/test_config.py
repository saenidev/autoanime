from pathlib import Path

import pytest

from autoanime.config import DEFAULT_CONFIG, generate_default_config, load_config


class TestGenerateDefaultConfig:
    def test_creates_file(self, tmp_path):
        config_path = tmp_path / "config.toml"
        path = generate_default_config(path=config_path)
        assert path.exists()

    def test_content_has_sections(self, tmp_path):
        config_path = tmp_path / "config.toml"
        generate_default_config(path=config_path)
        content = config_path.read_text()
        assert "[qbittorrent]" in content
        assert "[defaults]" in content
        assert "[nyaa]" in content

    def test_creates_parent_dirs(self, tmp_path):
        config_path = tmp_path / "sub" / "dir" / "config.toml"
        generate_default_config(path=config_path)
        assert config_path.exists()


class TestLoadConfig:
    def test_load_defaults(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)
        config = load_config(path=config_path)

        assert config.qbittorrent.host == "localhost"
        assert config.qbittorrent.port == 8080
        assert config.qbittorrent.username == "admin"
        assert config.qbittorrent.password == "adminadmin"
        assert config.defaults.quality == "1080p"
        assert config.defaults.group_priority == ["SubsPlease", "Erai-raws", "Judas"]
        assert config.defaults.max_torrent_size_mb == 4000
        assert config.nyaa.mirrors == ["nyaa.si", "nyaa.land"]
        assert config.nyaa.category == "1_2"
        assert config.nyaa.filter == 2
        assert config.nyaa.poll_interval_minutes == 15

    def test_load_custom(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            """\
[qbittorrent]
host = "192.168.1.100"
port = 9090
username = "user"
password = "secret"

[defaults]
quality = "720p"
group_priority = ["Erai-raws"]
max_torrent_size_mb = 2000

[nyaa]
mirrors = ["nyaa.si"]
category = "1_2"
filter = 0
poll_interval_minutes = 30
"""
        )
        config = load_config(path=config_path)
        assert config.qbittorrent.host == "192.168.1.100"
        assert config.qbittorrent.port == 9090
        assert config.defaults.quality == "720p"
        assert config.defaults.group_priority == ["Erai-raws"]
        assert config.nyaa.poll_interval_minutes == 30

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config(path=Path("/nonexistent/config.toml"))

    def test_roundtrip(self, tmp_path):
        config_path = tmp_path / "config.toml"
        generate_default_config(path=config_path)
        config = load_config(path=config_path)
        assert config.qbittorrent.host == "localhost"
        assert config.defaults.quality == "1080p"
