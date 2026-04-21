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

    def test_add_show(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)
        state_path = tmp_path / "state.json"

        runner = CliRunner()
        with (
            patch("autoanime.cli.search_anime", return_value=self._mock_results()),
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value={}),
            patch("autoanime.cli.save_state") as mock_save,
        ):
            result = runner.invoke(main, ["add", "Frieren"], input="y\n")

        assert result.exit_code == 0
        assert "Now tracking Sousou no Frieren" in result.output
        mock_save.assert_called_once()
        shows = mock_save.call_args[0][0]
        assert "sousou-no-frieren" in shows

    def test_add_with_from_ep(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(DEFAULT_CONFIG)

        runner = CliRunner()
        with (
            patch("autoanime.cli.search_anime", return_value=self._mock_results()),
            patch("autoanime.cli.load_config", return_value=__import__("autoanime.config", fromlist=["load_config"]).load_config(config_path)),
            patch("autoanime.cli.load_state", return_value={}),
            patch("autoanime.cli.save_state") as mock_save,
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

    def test_check_batch_queues_overflow(self, tmp_path):
        """With max_concurrent=1, a batch of 3 new eps should queue eps 2-3 as paused."""
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

        # Ep 1 should be the one downloaded (active), eps 2-3 queued
        lines = result.output.splitlines()
        dl_line = next(line for line in lines if "Would download" in line)
        assert "Frieren - 01" in dl_line
        queue_lines = [line for line in lines if "Would queue" in line]
        assert len(queue_lines) == 2
        assert any("Frieren - 02" in line for line in queue_lines)
        assert any("Frieren - 03" in line for line in queue_lines)

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
