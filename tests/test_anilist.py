from autoanime.anilist import _parse_search_response, get_air_day


class TestParseSearchResponse:
    def test_basic(self):
        data = {
            "data": {
                "Page": {
                    "media": [
                        {
                            "id": 154587,
                            "title": {
                                "romaji": "Sousou no Frieren",
                                "english": "Frieren: Beyond Journey's End",
                                "native": "葬送のフリーレン",
                            },
                            "synonyms": ["Frieren"],
                            "episodes": 28,
                            "status": "FINISHED",
                            "nextAiringEpisode": None,
                        }
                    ]
                }
            }
        }
        results = _parse_search_response(data)
        assert len(results) == 1
        r = results[0]
        assert r.id == 154587
        assert r.title_romaji == "Sousou no Frieren"
        assert r.title_english == "Frieren: Beyond Journey's End"
        assert r.episodes == 28
        assert r.status == "FINISHED"
        assert r.next_airing_at is None

    def test_with_airing(self):
        data = {
            "data": {
                "Page": {
                    "media": [
                        {
                            "id": 1,
                            "title": {"romaji": "Test", "english": None, "native": None},
                            "synonyms": [],
                            "episodes": None,
                            "status": "RELEASING",
                            "nextAiringEpisode": {
                                "airingAt": 1700000000,
                                "episode": 5,
                            },
                        }
                    ]
                }
            }
        }
        results = _parse_search_response(data)
        assert results[0].next_airing_at == 1700000000
        assert results[0].next_episode == 5

    def test_multiple_results(self):
        data = {
            "data": {
                "Page": {
                    "media": [
                        {
                            "id": i,
                            "title": {"romaji": f"Show {i}", "english": None, "native": None},
                            "synonyms": [],
                            "episodes": 12,
                            "status": "FINISHED",
                            "nextAiringEpisode": None,
                        }
                        for i in range(5)
                    ]
                }
            }
        }
        results = _parse_search_response(data)
        assert len(results) == 5

    def test_empty_response(self):
        data = {"data": {"Page": {"media": []}}}
        assert _parse_search_response(data) == []

    def test_missing_fields(self):
        data = {"data": {"Page": {"media": []}}}
        assert _parse_search_response(data) == []


class TestGetAirDay:
    def test_returns_weekday(self):
        # 1700000000 = 2023-11-14 22:13:20 UTC (Tuesday)
        assert get_air_day(1700000000) == "Tuesday"

    def test_none_input(self):
        assert get_air_day(None) is None

    def test_zero(self):
        assert get_air_day(0) is None
