from autoanime.download_plan import plan_downloads


def _entry(ep: int, title: str | None = None) -> dict:
    return {
        "title": title or f"[SubsPlease] Show - {ep:02d} (1080p) [HASH].mkv",
        "info_hash": f"hash{ep:02d}",
        "magnet": f"magnet:?xt=urn:btih:hash{ep:02d}",
        "episode": ep,
        "group": "SubsPlease",
        "quality": "1080p",
        "size_bytes": 500_000_000,
        "seeders": 100,
        "is_batch": False,
        "version": 1,
    }


def _torrent(name: str, state: str, thash: str) -> dict:
    return {"name": name, "state": state, "hash": thash}


class TestPlanDownloads:
    def test_empty_state_fills_one_active(self):
        new = [_entry(1), _entry(2), _entry(3), _entry(4)]
        plan = plan_downloads(new, existing_torrents=[], max_concurrent=1)
        assert [e["episode"] for e in plan.to_add_active] == [1]
        assert [e["episode"] for e in plan.to_add_paused] == [2, 3, 4]
        assert plan.to_resume_hashes == []

    def test_max_concurrent_two(self):
        new = [_entry(1), _entry(2), _entry(3), _entry(4)]
        plan = plan_downloads(new, existing_torrents=[], max_concurrent=2)
        assert [e["episode"] for e in plan.to_add_active] == [1, 2]
        assert [e["episode"] for e in plan.to_add_paused] == [3, 4]

    def test_active_slot_occupied_queues_all_new(self):
        existing = [_torrent("[SubsPlease] Show - 01 (1080p) [A].mkv", "downloading", "A")]
        new = [_entry(2), _entry(3)]
        plan = plan_downloads(new, existing_torrents=existing, max_concurrent=1)
        assert plan.to_add_active == []
        assert [e["episode"] for e in plan.to_add_paused] == [2, 3]
        assert plan.to_resume_hashes == []

    def test_resumes_earliest_paused_when_slot_free(self):
        existing = [
            _torrent("[SubsPlease] Show - 05 (1080p) [E].mkv", "stoppedDL", "E"),
            _torrent("[SubsPlease] Show - 02 (1080p) [B].mkv", "pausedDL", "B"),
            _torrent("[SubsPlease] Show - 03 (1080p) [C].mkv", "stoppedDL", "C"),
        ]
        plan = plan_downloads(new_episodes=[], existing_torrents=existing, max_concurrent=1)
        # Earliest paused (ep 2) should be resumed
        assert plan.to_resume_hashes == ["B"]
        assert plan.to_add_active == []
        assert plan.to_add_paused == []

    def test_resume_multiple_when_concurrency_allows(self):
        existing = [
            _torrent("[SubsPlease] Show - 02 (1080p) [B].mkv", "pausedDL", "B"),
            _torrent("[SubsPlease] Show - 03 (1080p) [C].mkv", "pausedDL", "C"),
            _torrent("[SubsPlease] Show - 04 (1080p) [D].mkv", "pausedDL", "D"),
        ]
        plan = plan_downloads(new_episodes=[], existing_torrents=existing, max_concurrent=2)
        assert plan.to_resume_hashes == ["B", "C"]

    def test_active_plus_paused_mixed(self):
        existing = [
            _torrent("[SubsPlease] Show - 01 (1080p) [A].mkv", "downloading", "A"),
            _torrent("[SubsPlease] Show - 02 (1080p) [B].mkv", "pausedDL", "B"),
        ]
        new = [_entry(3)]
        plan = plan_downloads(new, existing_torrents=existing, max_concurrent=1)
        # Ep 1 already active, so ep 2 stays paused, ep 3 queued
        assert plan.to_resume_hashes == []
        assert plan.to_add_active == []
        assert [e["episode"] for e in plan.to_add_paused] == [3]

    def test_completed_torrents_dont_count_as_active(self):
        """stoppedUP / uploading means done — shouldn't block new active downloads."""
        existing = [
            _torrent("[SubsPlease] Show - 01 (1080p) [A].mkv", "stoppedUP", "A"),
            _torrent("[SubsPlease] Show - 02 (1080p) [B].mkv", "uploading", "B"),
        ]
        new = [_entry(3)]
        plan = plan_downloads(new, existing_torrents=existing, max_concurrent=1)
        assert [e["episode"] for e in plan.to_add_active] == [3]

    def test_preserves_episode_order_in_added(self):
        # Feed in unsorted order
        new = [_entry(5), _entry(1), _entry(3), _entry(2)]
        plan = plan_downloads(new, existing_torrents=[], max_concurrent=1)
        assert [e["episode"] for e in plan.to_add_active] == [1]
        assert [e["episode"] for e in plan.to_add_paused] == [2, 3, 5]

    def test_zero_max_concurrent_means_unlimited(self):
        """0 or negative max_concurrent = concurrent mode, nothing paused."""
        new = [_entry(1), _entry(2), _entry(3), _entry(4)]
        plan = plan_downloads(new, existing_torrents=[], max_concurrent=0)
        assert [e["episode"] for e in plan.to_add_active] == [1, 2, 3, 4]
        assert plan.to_add_paused == []

    def test_unlimited_resumes_all_paused(self):
        existing = [
            _torrent("[SubsPlease] Show - 03 (1080p) [C].mkv", "pausedDL", "C"),
            _torrent("[SubsPlease] Show - 02 (1080p) [B].mkv", "stoppedDL", "B"),
        ]
        plan = plan_downloads(new_episodes=[], existing_torrents=existing, max_concurrent=0)
        # Both resumed, ordered earliest first
        assert plan.to_resume_hashes == ["B", "C"]

    def test_negative_max_concurrent_means_unlimited(self):
        new = [_entry(1), _entry(2)]
        plan = plan_downloads(new, existing_torrents=[], max_concurrent=-1)
        assert [e["episode"] for e in plan.to_add_active] == [1, 2]
        assert plan.to_add_paused == []

    def test_empty_everything(self):
        plan = plan_downloads([], existing_torrents=[], max_concurrent=1)
        assert plan.to_add_active == []
        assert plan.to_add_paused == []
        assert plan.to_resume_hashes == []
