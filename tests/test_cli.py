from unittest.mock import patch

from click.testing import CliRunner

from autoanime.anilist import AniListResult
from autoanime.cli import main
from autoanime.config import DEFAULT_CONFIG
from autoanime.state import Show, load_state, save_state


class TestMainNoSubcommand:
    def test_generates_config_when_missing(self, tmp_path):
        config_path = tmp_path / "config.toml"
        runner = CliRunner()
        with (
            patch("autoanime.cli.CONFIG_PATH", config_path),
            patch("autoanime.config.CONFIG_PATH", config_path),
            patch("autoanime.config.CONFIG_DIR", tmp_path),
        ):
            result = runner.invoke(main)
        assert result.exit_code == 0
        assert "Generated default config" in result.output
        assert config_path.exists()

    def test_shows_help_when_config_exists(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)
        runner = CliRunner()
        with patch("autoanime.cli.CONFIG_PATH", config_path):
            result = runner.invoke(main)
        assert result.exit_code == 0
        assert "auto-download anime" in result.output


class TestAddCommand:
    def _mock_results(self):
        return [
            AniListResult(
                id=154587,
                title_romaji="Sousou no Frieren",
                title_english="Frieren: Beyond Journey's End",
                title_native="葬送のフリーレン",
                synonyms=["Frieren"],
                episodes=28,
                status="FINISHED",
                next_airing_at=None,
                next_episode=None,
            )
        ]

    def _entry(self, **kwargs):
        base = {
            "title": "[SubsPlease] Sousou no Frieren - 01 (1080p) [HASH].mkv",
            "info_hash": "abc",
            "magnet": "magnet:?",
            "size_bytes": 500 * 1024**2,
            "seeders": 100,
            "group": "SubsPlease",
            "episode": 1,
            "quality": "1080p",
            "is_batch": False,
            "version": 1,
        }
        base.update(kwargs)
        return base

    def test_add_show_falls_back_when_no_nyaa_hits(self, tmp_path):
        """0 Nyaa hits → no picker, group_override stays None, add still completes."""
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        runner = CliRunner()
        with (
            patch("autoanime.cli.search_anime", return_value=self._mock_results()),
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value={}),
            patch("autoanime.cli.save_state") as mock_save,
            patch("autoanime.cli.fetch_rss", return_value=[]),
        ):
            result = runner.invoke(main, ["add", "Frieren"], input="y\n")

        assert result.exit_code == 0, result.output
        assert "Now tracking Sousou no Frieren" in result.output
        assert "No releases found on Nyaa yet" in result.output
        shows = mock_save.call_args[0][0]
        show = shows["sousou-no-frieren"]
        assert show.group_override is None
        # Query has no group prefix anymore
        assert show.search_query == "Sousou no Frieren 1080p"

    def test_add_show_with_picker(self, tmp_path):
        """Multiple groups in Nyaa results → picker, user choice saved as group_override."""
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        entries = [
            self._entry(group="Sokudo", episode=1, info_hash="s1"),
            self._entry(group="Sokudo", episode=2, info_hash="s2"),
            self._entry(group="DKB", episode=1, info_hash="d1"),
        ]
        runner = CliRunner()
        with (
            patch("autoanime.cli.search_anime", return_value=self._mock_results()),
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value={}),
            patch("autoanime.cli.save_state") as mock_save,
            patch("autoanime.cli.fetch_rss", return_value=entries),
        ):
            # y to anilist confirm, 2 picks DKB
            result = runner.invoke(main, ["add", "Frieren"], input="y\n2\n")

        assert result.exit_code == 0, result.output
        assert "Available release groups" in result.output
        shows = mock_save.call_args[0][0]
        # Sokudo has 2 eps so it's listed first; DKB is #2
        assert shows["sousou-no-frieren"].group_override == "DKB"

    def test_add_show_picker_default_first(self, tmp_path):
        """User just hits enter → defaults to first listed group."""
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        entries = [
            self._entry(group="SubsPlease", episode=1, info_hash="sp1"),
            self._entry(group="DKB", episode=1, info_hash="d1"),
        ]
        runner = CliRunner()
        with (
            patch("autoanime.cli.search_anime", return_value=self._mock_results()),
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value={}),
            patch("autoanime.cli.save_state") as mock_save,
            patch("autoanime.cli.fetch_rss", return_value=entries),
        ):
            # y, then empty for default
            result = runner.invoke(main, ["add", "Frieren"], input="y\n\n")

        assert result.exit_code == 0, result.output
        shows = mock_save.call_args[0][0]
        # SubsPlease is in default group_priority → sorted first → default pick
        assert shows["sousou-no-frieren"].group_override == "SubsPlease"

    def test_add_with_group_flag_skips_picker(self, tmp_path):
        """--group X bypasses Nyaa fetch + picker entirely."""
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        runner = CliRunner()
        with (
            patch("autoanime.cli.search_anime", return_value=self._mock_results()),
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value={}),
            patch("autoanime.cli.save_state") as mock_save,
            patch("autoanime.cli.fetch_rss") as mock_fetch,
        ):
            result = runner.invoke(
                main, ["add", "Frieren", "--group", "Sokudo"], input="y\n"
            )

        assert result.exit_code == 0, result.output
        mock_fetch.assert_not_called()
        shows = mock_save.call_args[0][0]
        assert shows["sousou-no-frieren"].group_override == "Sokudo"
        assert shows["sousou-no-frieren"].search_query == "Sousou no Frieren 1080p"

    def test_add_with_from_ep(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        runner = CliRunner()
        with (
            patch("autoanime.cli.search_anime", return_value=self._mock_results()),
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value={}),
            patch("autoanime.cli.save_state") as mock_save,
            patch("autoanime.cli.fetch_rss", return_value=[]),
        ):
            result = runner.invoke(
                main, ["add", "Frieren", "--from", "8"], input="y\n"
            )

        assert result.exit_code == 0
        assert "Episodes 1-7 marked as downloaded" in result.output
        shows = mock_save.call_args[0][0]
        assert shows["sousou-no-frieren"].downloaded_episodes == set(range(1, 8))

    def test_add_no_results(self):
        runner = CliRunner()
        with patch("autoanime.cli.search_anime", return_value=[]):
            result = runner.invoke(main, ["add", "nonexistent"])
        assert "No results found" in result.output

    def test_add_duplicate(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        existing = {
            "sousou-no-frieren": Show(
                anilist_id=154587, title="Sousou no Frieren"
            )
        }
        runner = CliRunner()
        with (
            patch("autoanime.cli.search_anime", return_value=self._mock_results()),
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value=existing),
        ):
            result = runner.invoke(main, ["add", "Frieren"], input="y\n")
        assert "Already tracking" in result.output


class TestListCommand:
    def test_list_empty(self):
        runner = CliRunner()
        with patch("autoanime.cli.load_state", return_value={}):
            result = runner.invoke(main, ["list"])
        assert "No shows tracked" in result.output

    def test_list_shows(self):
        shows = {
            "frieren": Show(
                anilist_id=1,
                title="Sousou no Frieren",
                total_episodes=28,
                airing_status="FINISHED",
                air_day="Friday",
                downloaded_episodes={1, 2, 3},
            )
        }
        runner = CliRunner()
        with patch("autoanime.cli.load_state", return_value=shows):
            result = runner.invoke(main, ["list"])
        assert "Sousou no Frieren" in result.output
        assert "3/28" in result.output

    def test_list_columns_aligned(self):
        """Regression: episode counts of different digit widths must not break alignment."""
        shows = {
            "a": Show(
                anilist_id=1,
                title="Short Show",
                total_episodes=12,
                airing_status="FINISHED",
                air_day="Fri",
                downloaded_episodes={1, 2},
            ),
            "b": Show(
                anilist_id=2,
                title="Long Show",
                total_episodes=None,
                airing_status="RELEASING",
                air_day="Sun",
                downloaded_episodes=set(range(1, 1120)),
            ),
        }
        runner = CliRunner()
        with patch("autoanime.cli.load_state", return_value=shows):
            result = runner.invoke(main, ["list"])
        lines = [line for line in result.output.splitlines() if "FINISHED" in line or "RELEASING" in line]
        assert len(lines) == 2
        status_cols = [line.index("FINISHED") if "FINISHED" in line else line.index("RELEASING") for line in lines]
        assert status_cols[0] == status_cols[1], f"Status column misaligned: {status_cols}"

    def test_list_skips_archived(self):
        shows = {
            "frieren": Show(
                anilist_id=1,
                title="Sousou no Frieren",
                archived=True,
            )
        }
        runner = CliRunner()
        with patch("autoanime.cli.load_state", return_value=shows):
            result = runner.invoke(main, ["list"])
        assert "Sousou no Frieren" not in result.output


class TestRemoveCommand:
    def test_remove_show(self):
        shows = {
            "frieren": Show(anilist_id=1, title="Sousou no Frieren"),
        }
        runner = CliRunner()
        with (
            patch("autoanime.cli.load_state", return_value=shows),
            patch("autoanime.cli.save_state") as mock_save,
        ):
            result = runner.invoke(main, ["remove", "Frieren"], input="y\n")
        assert "Removed Sousou no Frieren" in result.output
        mock_save.assert_called_once()

    def test_remove_no_match(self):
        runner = CliRunner()
        with patch("autoanime.cli.load_state", return_value={}):
            result = runner.invoke(main, ["remove", "nonexistent"])
        assert "No tracked show matching" in result.output

    def test_remove_empty_string_guarded(self):
        """Regression: `autoanime remove ""` must not match all shows."""
        shows = {
            "a": Show(anilist_id=1, title="Show A"),
            "b": Show(anilist_id=2, title="Show B"),
        }
        runner = CliRunner()
        with (
            patch("autoanime.cli.load_state", return_value=shows),
            patch("autoanime.cli.save_state") as mock_save,
        ):
            result = runner.invoke(main, ["remove", ""])
        assert "Please provide" in result.output
        mock_save.assert_not_called()


class TestCheckCommand:
    def test_check_dry_run(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        shows = {
            "frieren": Show(
                anilist_id=1,
                title="Frieren",
                search_query="SubsPlease Frieren 1080p",
                downloaded_episodes={1, 2},
            )
        }

        mock_entries = [
            {
                "title": "[SubsPlease] Frieren - 03 (1080p) [HASH].mkv",
                "info_hash": "abc123",
                "magnet": "magnet:?test",
                "size_bytes": 500_000_000,
                "seeders": 100,
                "group": "SubsPlease",
                "episode": 3,
                "quality": "1080p",
                "is_batch": False,
                "version": 1,
            }
        ]

        runner = CliRunner()
        with (
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value=shows),
            patch("autoanime.cli.save_state"),
            patch("autoanime.cli.fetch_rss", return_value=mock_entries),
        ):
            result = runner.invoke(main, ["check", "--dry-run"])

        assert result.exit_code == 0
        assert "[DRY RUN] Would download" in result.output
        assert "1 new episode(s)" in result.output

    def test_check_nothing_new(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        shows = {
            "frieren": Show(
                anilist_id=1,
                title="Frieren",
                search_query="SubsPlease Frieren 1080p",
                downloaded_episodes={1, 2, 3},
            )
        }

        runner = CliRunner()
        with (
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value=shows),
            patch("autoanime.cli.save_state"),
            patch("autoanime.cli.fetch_rss", return_value=[]),
        ):
            result = runner.invoke(main, ["check", "--dry-run"])

        assert result.exit_code == 0
        assert "nothing new" in result.output

    def test_check_batch_concurrent_by_default(self, tmp_path):
        """Default behavior: all new eps download concurrently, in episode order."""
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        shows = {
            "frieren": Show(
                anilist_id=1,
                title="Frieren",
                search_query="SubsPlease Frieren 1080p",
                downloaded_episodes=set(),
            )
        }

        def _mk(ep):
            return {
                "title": f"[SubsPlease] Frieren - {ep:02d} (1080p) [H].mkv",
                "info_hash": f"hash{ep}",
                "magnet": f"magnet:?xt=urn:btih:hash{ep}",
                "size_bytes": 500_000_000,
                "seeders": 100,
                "group": "SubsPlease",
                "episode": ep,
                "quality": "1080p",
                "is_batch": False,
                "version": 1,
            }

        runner = CliRunner()
        with (
            patch(
                "autoanime.cli.load_config",
                return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path),
            ),
            patch("autoanime.cli.load_state", return_value=shows),
            patch("autoanime.cli.save_state"),
            patch("autoanime.cli.fetch_rss", return_value=[_mk(3), _mk(1), _mk(2)]),
        ):
            result = runner.invoke(main, ["check", "--dry-run"])

        # All three download concurrently, listed in episode order (earliest first)
        lines = result.output.splitlines()
        dl_lines = [line for line in lines if "Would download" in line]
        assert len(dl_lines) == 3
        queue_lines = [line for line in lines if "Would queue" in line]
        assert queue_lines == []
        # Earliest first in the output
        assert "Frieren - 01" in dl_lines[0]
        assert "Frieren - 02" in dl_lines[1]
        assert "Frieren - 03" in dl_lines[2]

    def test_check_batch_serial_when_configured(self, tmp_path):
        """Opt-in: max_concurrent_per_show = 1 serializes to one at a time."""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            """\
[qbittorrent]
host = "localhost"
port = 8080
username = "admin"
password = "adminadmin"

[defaults]
quality = "1080p"
group_priority = ["SubsPlease"]
max_torrent_size_mb = 4000
max_concurrent_per_show = 1

[nyaa]
mirrors = ["nyaa.si"]
category = "1_2"
filter = 2
poll_interval_minutes = 60
"""
        )

        shows = {
            "frieren": Show(
                anilist_id=1,
                title="Frieren",
                search_query="SubsPlease Frieren 1080p",
                downloaded_episodes=set(),
            )
        }

        def _mk(ep):
            return {
                "title": f"[SubsPlease] Frieren - {ep:02d} (1080p) [H].mkv",
                "info_hash": f"hash{ep}",
                "magnet": f"magnet:?xt=urn:btih:hash{ep}",
                "size_bytes": 500_000_000,
                "seeders": 100,
                "group": "SubsPlease",
                "episode": ep,
                "quality": "1080p",
                "is_batch": False,
                "version": 1,
            }

        runner = CliRunner()
        with (
            patch(
                "autoanime.cli.load_config",
                return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path),
            ),
            patch("autoanime.cli.load_state", return_value=shows),
            patch("autoanime.cli.save_state"),
            patch("autoanime.cli.fetch_rss", return_value=[_mk(1), _mk(2), _mk(3)]),
        ):
            result = runner.invoke(main, ["check", "--dry-run"])

        lines = result.output.splitlines()
        dl_lines = [line for line in lines if "Would download" in line]
        queue_lines = [line for line in lines if "Would queue" in line]
        assert len(dl_lines) == 1
        assert "Frieren - 01" in dl_lines[0]
        assert len(queue_lines) == 2

    def test_check_honors_group_override(self, tmp_path):
        """Show with group_override='Sokudo' must only download Sokudo releases."""
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        shows = {
            "nippon": Show(
                anilist_id=1,
                title="Nippon Sangoku",
                search_query="Nippon Sangoku 1080p",
                group_override="Sokudo",
                downloaded_episodes=set(),
            )
        }

        def _mk(group, ep, ihash):
            return {
                "title": f"[{group}] Nippon Sangoku - S01E{ep:02d} (1080p) [H].mkv",
                "info_hash": ihash,
                "magnet": f"magnet:?xt=urn:btih:{ihash}",
                "size_bytes": 500_000_000,
                "seeders": 100,
                "group": group,
                "episode": ep,
                "quality": "1080p",
                "is_batch": False,
                "version": 1,
            }

        entries = [
            _mk("Erai-raws", 1, "e1"),
            _mk("Erai-raws", 2, "e2"),
            _mk("Sokudo", 1, "s1"),
            _mk("Sokudo", 2, "s2"),
        ]

        runner = CliRunner()
        with (
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value=shows),
            patch("autoanime.cli.save_state"),
            patch("autoanime.cli.fetch_rss", return_value=entries) as mock_fetch,
        ):
            result = runner.invoke(main, ["check", "--dry-run"])

        assert result.exit_code == 0, result.output
        # Only Sokudo episodes appear in download lines
        lines = [line for line in result.output.splitlines() if "Would download" in line]
        assert len(lines) == 2
        assert all("[Sokudo]" in line for line in lines)
        # filter=0 was used (because group_override is set)
        # fetch_rss(query, mirrors, category, filter_)
        assert mock_fetch.call_args.args[3] == 0

    def test_check_no_shows(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        runner = CliRunner()
        with (
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value={}),
            patch("autoanime.cli.save_state"),
        ):
            result = runner.invoke(main, ["check", "--dry-run"])
        assert result.exit_code == 0
