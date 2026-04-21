import json

from autoanime.state import Show, load_state, make_slug, save_state


class TestMakeSlug:
    def test_simple(self):
        assert make_slug("Sousou no Frieren") == "sousou-no-frieren"

    def test_strips_special_chars(self):
        assert make_slug("Frieren: Beyond Journey's End") == "frieren-beyond-journeys-end"

    def test_collapses_spaces(self):
        assert make_slug("  Some   Show  ") == "some-show"

    def test_lowercase(self):
        assert make_slug("DANDADAN") == "dandadan"

    def test_numbers(self):
        assert make_slug("86 Eighty Six") == "86-eighty-six"


class TestSaveAndLoad:
    def test_roundtrip(self, tmp_path):
        state_path = tmp_path / "state.json"
        shows = {
            "frieren": Show(
                anilist_id=154587,
                title="Sousou no Frieren",
                downloaded_episodes={1, 2, 3},
            )
        }
        save_state(shows, path=state_path)
        loaded = load_state(path=state_path)

        assert "frieren" in loaded
        assert loaded["frieren"].downloaded_episodes == {1, 2, 3}
        assert loaded["frieren"].title == "Sousou no Frieren"
        assert loaded["frieren"].anilist_id == 154587

    def test_empty_state(self, tmp_path):
        state_path = tmp_path / "state.json"
        shows = load_state(path=state_path)
        assert shows == {}

    def test_episode_set_sorted_in_json(self, tmp_path):
        state_path = tmp_path / "state.json"
        shows = {
            "test": Show(
                anilist_id=1,
                title="Test",
                downloaded_episodes={5, 2, 8, 1},
            )
        }
        save_state(shows, path=state_path)

        raw = json.loads(state_path.read_text())
        assert raw["shows"]["test"]["downloaded_episodes"] == [1, 2, 5, 8]

    def test_atomic_write(self, tmp_path):
        state_path = tmp_path / "state.json"
        shows = {
            "test": Show(anilist_id=1, title="Test"),
        }
        save_state(shows, path=state_path)
        assert state_path.exists()
        assert not state_path.with_suffix(".tmp").exists()

    def test_preserves_all_fields(self, tmp_path):
        state_path = tmp_path / "state.json"
        shows = {
            "test": Show(
                anilist_id=42,
                title="Test Show",
                alt_titles=["Alt1", "Alt2"],
                search_query="SubsPlease Test 1080p",
                group_override="Erai-raws",
                quality_override="720p",
                download_dir="/tmp/anime",
                total_episodes=12,
                airing_status="RELEASING",
                air_day="Friday",
                downloaded_episodes={1, 2, 3},
                nyaa_fingerprint="[SubsPlease] Test - {ep}",
                archived=False,
            )
        }
        save_state(shows, path=state_path)
        loaded = load_state(path=state_path)

        s = loaded["test"]
        assert s.anilist_id == 42
        assert s.alt_titles == ["Alt1", "Alt2"]
        assert s.search_query == "SubsPlease Test 1080p"
        assert s.group_override == "Erai-raws"
        assert s.quality_override == "720p"
        assert s.download_dir == "/tmp/anime"
        assert s.total_episodes == 12
        assert s.airing_status == "RELEASING"
        assert s.air_day == "Friday"
        assert s.nyaa_fingerprint == "[SubsPlease] Test - {ep}"
        assert s.archived is False

    def test_multiple_shows(self, tmp_path):
        state_path = tmp_path / "state.json"
        shows = {
            "show-a": Show(anilist_id=1, title="Show A"),
            "show-b": Show(anilist_id=2, title="Show B"),
            "show-c": Show(anilist_id=3, title="Show C"),
        }
        save_state(shows, path=state_path)
        loaded = load_state(path=state_path)
        assert len(loaded) == 3
        assert set(loaded.keys()) == {"show-a", "show-b", "show-c"}
