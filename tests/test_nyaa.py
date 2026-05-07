from autoanime.nyaa import (
    _parse_size,
    build_magnet,
    parse_title,
    rank_entries,
    summarize_groups,
)


class TestParseTitle:
    def test_subsplease_standard(self):
        r = parse_title("[SubsPlease] Sousou no Frieren - 28 (1080p) [A1B2C3D4].mkv")
        assert r["group"] == "SubsPlease"
        assert r["episode"] == 28
        assert r["quality"] == "1080p"
        assert r["is_batch"] is False
        assert r["version"] == 1

    def test_erai_raws(self):
        r = parse_title(
            "[Erai-raws] Sousou no Frieren - 28 [1080p][Multiple Subtitle].mkv"
        )
        assert r["group"] == "Erai-raws"
        assert r["episode"] == 28
        assert r["quality"] == "1080p"
        assert r["is_batch"] is False

    def test_sxxexx_format(self):
        r = parse_title("[Judas] Frieren - S01E28.mkv")
        assert r["group"] == "Judas"
        assert r["episode"] == 28
        assert r["quality"] is None

    def test_batch_with_range(self):
        r = parse_title("[SubsPlease] Sousou no Frieren (01-28) (1080p) [Batch]")
        assert r["is_batch"] is True

    def test_batch_with_tilde_range(self):
        r = parse_title("[SubsPlease] Dandadan (01~12) (1080p) [Batch]")
        assert r["is_batch"] is True

    def test_batch_keyword_only(self):
        r = parse_title("[SubsPlease] Frieren Batch (1080p)")
        assert r["is_batch"] is True

    def test_version_v2(self):
        r = parse_title("[Erai-raws] Dandadan - 05v2 [1080p].mkv")
        assert r["episode"] == 5
        assert r["version"] == 2

    def test_version_v3(self):
        r = parse_title("[SubsPlease] Some Show - 12v3 (1080p) [HASH].mkv")
        assert r["episode"] == 12
        assert r["version"] == 3

    def test_720p(self):
        r = parse_title("[SubsPlease] Dandadan - 12 (720p) [HASH].mkv")
        assert r["quality"] == "720p"

    def test_480p(self):
        r = parse_title("[SubsPlease] Dandadan - 12 (480p) [HASH].mkv")
        assert r["quality"] == "480p"

    def test_2160p(self):
        r = parse_title("[SomeGroup] Big Show - 01 (2160p) [HASH].mkv")
        assert r["quality"] == "2160p"

    def test_no_group(self):
        r = parse_title("Frieren - 28 (1080p).mkv")
        assert r["group"] is None
        assert r["episode"] == 28

    def test_no_episode(self):
        r = parse_title("[SubsPlease] Frieren OST (FLAC)")
        assert r["episode"] is None

    def test_episode_zero(self):
        r = parse_title("[SubsPlease] Some Show - 0 (1080p) [HASH].mkv")
        assert r["episode"] == 0

    def test_high_episode_number(self):
        r = parse_title("[SubsPlease] One Piece - 1120 (1080p) [HASH].mkv")
        assert r["episode"] == 1120

    def test_show_with_number_in_name(self):
        r = parse_title("[SubsPlease] 86 - Eighty Six - 12 (1080p) [HASH].mkv")
        assert r["episode"] == 12

    def test_sxxexx_case_insensitive(self):
        r = parse_title("[Group] Show - s02e05.mkv")
        assert r["episode"] == 5

    def test_not_batch_when_sxxexx(self):
        r = parse_title("[Group] Show - S01E01-E12.mkv")
        assert r["is_batch"] is False

    def test_batch_dash_range_without_parens(self):
        """Regression: [Erai-raws] Dandadan - 01-12 (1080p) was parsed as ep=1."""
        r = parse_title("[Erai-raws] Dandadan - 01-12 (1080p).mkv")
        assert r["is_batch"] is True

    def test_batch_bracket_range(self):
        r = parse_title("[Group] Show [01-12] (1080p).mkv")
        assert r["is_batch"] is True

    def test_batch_large_episode_range(self):
        r = parse_title("[Group] Long Show - 105-110 (1080p).mkv")
        assert r["is_batch"] is True


class TestParseSize:
    def test_gib(self):
        assert _parse_size("1.4 GiB") == int(1.4 * 1024**3)

    def test_mib(self):
        assert _parse_size("500 MiB") == 500 * 1024**2

    def test_kib(self):
        assert _parse_size("800 KiB") == 800 * 1024

    def test_tib(self):
        assert _parse_size("1.0 TiB") == 1024**4

    def test_zero(self):
        assert _parse_size("0 MiB") == 0

    def test_invalid(self):
        assert _parse_size("unknown") == 0

    def test_empty(self):
        assert _parse_size("") == 0


class TestBuildMagnet:
    def test_basic(self):
        m = build_magnet("abc123", "Test Title")
        assert m.startswith("magnet:?xt=urn:btih:abc123")
        assert "dn=" in m
        assert "tr=" in m


class TestRankEntries:
    def _make_entry(self, **kwargs):
        base = {
            "title": "test",
            "info_hash": "abc",
            "magnet": "magnet:?test",
            "size_bytes": 500_000_000,
            "seeders": 50,
            "group": "SubsPlease",
            "episode": 1,
            "quality": "1080p",
            "is_batch": False,
            "version": 1,
        }
        base.update(kwargs)
        return base

    def test_priority_ordering(self):
        entries = [
            self._make_entry(group="Judas", seeders=10),
            self._make_entry(group="SubsPlease", seeders=100),
            self._make_entry(group="Erai-raws", seeders=50),
        ]
        ranked = rank_entries(
            entries, ["SubsPlease", "Erai-raws", "Judas"], "1080p", 4000
        )
        assert [e["group"] for e in ranked] == ["SubsPlease", "Erai-raws", "Judas"]

    def test_seeder_tiebreak(self):
        entries = [
            self._make_entry(group="SubsPlease", seeders=10, info_hash="a"),
            self._make_entry(group="SubsPlease", seeders=100, info_hash="b"),
        ]
        ranked = rank_entries(entries, ["SubsPlease"], "1080p", 4000)
        assert ranked[0]["seeders"] == 100

    def test_filters_batch(self):
        entries = [self._make_entry(is_batch=True)]
        assert rank_entries(entries, ["SubsPlease"], "1080p", 4000) == []

    def test_filters_no_episode(self):
        entries = [self._make_entry(episode=None)]
        assert rank_entries(entries, ["SubsPlease"], "1080p", 4000) == []

    def test_filters_wrong_quality(self):
        entries = [self._make_entry(quality="720p")]
        assert rank_entries(entries, ["SubsPlease"], "1080p", 4000) == []

    def test_filters_oversized(self):
        entries = [self._make_entry(size_bytes=5_000_000_000)]
        assert rank_entries(entries, ["SubsPlease"], "1080p", 4000) == []

    def test_allows_no_quality(self):
        entries = [self._make_entry(quality=None)]
        ranked = rank_entries(entries, ["SubsPlease"], "1080p", 4000)
        assert len(ranked) == 1

    def test_allows_zero_size(self):
        entries = [self._make_entry(size_bytes=0)]
        ranked = rank_entries(entries, ["SubsPlease"], "1080p", 4000)
        assert len(ranked) == 1

    def test_unknown_group_ranked_last(self):
        entries = [
            self._make_entry(group="Unknown", seeders=1000),
            self._make_entry(group="SubsPlease", seeders=10),
        ]
        ranked = rank_entries(entries, ["SubsPlease"], "1080p", 4000)
        assert ranked[0]["group"] == "SubsPlease"

    def test_strict_group_filters_out_others(self):
        entries = [
            self._make_entry(group="Erai-raws", info_hash="a"),
            self._make_entry(group="Sokudo", info_hash="b"),
            self._make_entry(group="DKB", info_hash="c"),
        ]
        ranked = rank_entries(
            entries, ["SubsPlease"], "1080p", 4000, strict_group="Sokudo"
        )
        assert [e["group"] for e in ranked] == ["Sokudo"]

    def test_strict_group_none_keeps_all(self):
        entries = [
            self._make_entry(group="Erai-raws", info_hash="a"),
            self._make_entry(group="Sokudo", info_hash="b"),
        ]
        ranked = rank_entries(
            entries, ["SubsPlease"], "1080p", 4000, strict_group=None
        )
        assert len(ranked) == 2


class TestSummarizeGroups:
    def _entry(self, **kwargs):
        base = {
            "title": "[X] Show - 01 (1080p) [HASH].mkv",
            "info_hash": "abc",
            "magnet": "magnet:?",
            "size_bytes": 500 * 1024**2,
            "seeders": 10,
            "group": "X",
            "episode": 1,
            "quality": "1080p",
            "is_batch": False,
            "version": 1,
        }
        base.update(kwargs)
        return base

    def test_groups_by_release_group(self):
        entries = [
            self._entry(group="Sokudo", episode=1),
            self._entry(group="Sokudo", episode=2),
            self._entry(group="DKB", episode=1),
        ]
        summaries = summarize_groups(entries, [])
        names = sorted(s.group for s in summaries)
        assert names == ["DKB", "Sokudo"]

    def test_episode_count_uses_distinct_episodes(self):
        entries = [
            self._entry(group="A", episode=1, info_hash="a"),
            self._entry(group="A", episode=1, info_hash="b"),
            self._entry(group="A", episode=2, info_hash="c"),
        ]
        summaries = summarize_groups(entries, [])
        assert summaries[0].episode_count == 2

    def test_latest_episode(self):
        entries = [
            self._entry(group="A", episode=3),
            self._entry(group="A", episode=5),
            self._entry(group="A", episode=1),
        ]
        summaries = summarize_groups(entries, [])
        assert summaries[0].latest_episode == 5

    def test_avg_size_mb(self):
        entries = [
            self._entry(group="A", size_bytes=1000 * 1024**2),
            self._entry(group="A", size_bytes=1400 * 1024**2),
        ]
        summaries = summarize_groups(entries, [])
        assert summaries[0].avg_size_mb == 1200

    def test_skips_entries_with_no_group(self):
        entries = [
            self._entry(group=None, episode=1),
            self._entry(group="A", episode=1),
        ]
        summaries = summarize_groups(entries, [])
        assert [s.group for s in summaries] == ["A"]

    def test_skips_batches(self):
        entries = [
            self._entry(group="A", is_batch=True, episode=None),
            self._entry(group="A", is_batch=False, episode=1),
        ]
        summaries = summarize_groups(entries, [])
        assert summaries[0].episode_count == 1

    def test_sorted_by_total_seeders_desc(self):
        entries = [
            self._entry(group="A", episode=1, seeders=50, info_hash="a"),
            self._entry(group="B", episode=1, seeders=200, info_hash="b"),
            self._entry(group="C", episode=1, seeders=100, info_hash="c"),
        ]
        summaries = summarize_groups(entries, [])
        assert [s.group for s in summaries] == ["B", "C", "A"]

    def test_total_seeders_is_sum_across_releases(self):
        entries = [
            self._entry(group="A", episode=1, seeders=30, info_hash="a1"),
            self._entry(group="A", episode=2, seeders=70, info_hash="a2"),
        ]
        summaries = summarize_groups(entries, [])
        assert summaries[0].total_seeders == 100

    def test_seeders_override_preferred_badge(self):
        """Preferred is informational; a non-preferred group with more seeders sorts first."""
        entries = [
            self._entry(group="Sokudo", episode=1, seeders=500, info_hash="s"),
            self._entry(group="SubsPlease", episode=1, seeders=10, info_hash="sp"),
        ]
        summaries = summarize_groups(entries, ["SubsPlease"])
        assert [s.group for s in summaries] == ["Sokudo", "SubsPlease"]
        # is_preferred is still set correctly even though sort ignored it
        assert summaries[1].is_preferred is True
        assert summaries[0].is_preferred is False

    def test_episode_count_tiebreak_when_seeders_equal(self):
        entries = [
            self._entry(group="A", episode=1, seeders=10, info_hash="a"),
            self._entry(group="B", episode=1, seeders=10, info_hash="b1"),
            self._entry(group="B", episode=2, seeders=10, info_hash="b2"),
            self._entry(group="B", episode=3, seeders=10, info_hash="b3"),
            self._entry(group="C", episode=1, seeders=10, info_hash="c1"),
            self._entry(group="C", episode=2, seeders=10, info_hash="c2"),
        ]
        summaries = summarize_groups(entries, [])
        # B (30) > C (20) > A (10) by total_seeders since seeders/release equal
        assert [s.group for s in summaries] == ["B", "C", "A"]

    def test_codec_hint_av1(self):
        entries = [
            self._entry(
                group="A",
                title="[A] Show S01E01 [1080p WEB-DL AV1][Dual Audio]",
            )
        ]
        summaries = summarize_groups(entries, [])
        assert summaries[0].codec_hint == "AV1"

    def test_codec_hint_hevc(self):
        entries = [
            self._entry(
                group="A",
                title="[A] Show - S01E01 [1080p][HEVC x265 10bit][Dual-Audio]",
            )
        ]
        summaries = summarize_groups(entries, [])
        assert summaries[0].codec_hint == "HEVC"

    def test_codec_hint_h264(self):
        entries = [
            self._entry(
                group="A",
                title="[A] Show - 01 [1080p AMZN WEB-DL AVC EAC3]",
            )
        ]
        summaries = summarize_groups(entries, [])
        assert summaries[0].codec_hint == "x264"

    def test_audio_hint_dual_audio(self):
        entries = [
            self._entry(
                group="A",
                title="[A] Show - 01 [1080p][Dual-Audio]",
            )
        ]
        summaries = summarize_groups(entries, [])
        assert summaries[0].audio_hint == "dual-audio"

    def test_audio_hint_none_when_absent(self):
        entries = [self._entry(group="A", title="[A] Show - 01 [1080p]")]
        summaries = summarize_groups(entries, [])
        assert summaries[0].audio_hint is None

    def test_empty_input(self):
        assert summarize_groups([], []) == []
