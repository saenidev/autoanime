from autoanime.nyaa import _parse_size, build_magnet, parse_title, rank_entries


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
