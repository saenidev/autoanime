from unittest.mock import patch

from autoanime.config import DEFAULT_CONFIG
from autoanime.scheduler import generate_plist


class TestGeneratePlist:
    def test_explicit_interval(self):
        plist = generate_plist(bin_path="/usr/local/bin/autoanime", interval_seconds=3600)
        assert "<integer>3600</integer>" in plist
        assert "/usr/local/bin/autoanime" in plist

    def test_reads_config_interval(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            """\
[nyaa]
mirrors = ["nyaa.si"]
category = "1_2"
filter = 2
poll_interval_minutes = 60
"""
        )
        with patch("autoanime.config.CONFIG_PATH", config_path):
            plist = generate_plist(bin_path="/bin/autoanime")
        assert "<integer>3600</integer>" in plist

    def test_fallback_when_no_config(self, tmp_path):
        missing = tmp_path / "nope.toml"
        with patch("autoanime.config.CONFIG_PATH", missing):
            plist = generate_plist(bin_path="/bin/autoanime")
        assert "<integer>900</integer>" in plist

    def test_enforces_minimum_interval(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            """\
[nyaa]
poll_interval_minutes = 0
"""
        )
        with patch("autoanime.config.CONFIG_PATH", config_path):
            plist = generate_plist(bin_path="/bin/autoanime")
        # Should enforce minimum 60s (= 1 min)
        assert "<integer>60</integer>" in plist

    def test_default_config_gives_15_min(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)
        with patch("autoanime.config.CONFIG_PATH", config_path):
            plist = generate_plist(bin_path="/bin/autoanime")
        assert "<integer>900</integer>" in plist
