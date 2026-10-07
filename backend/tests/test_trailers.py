import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import trailers  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_caches(monkeypatch):
    trailers.clear_caches()
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    # No test may touch the network.
    monkeypatch.setattr(trailers, "_get_json", lambda url, params=None, timeout=6: {})
    monkeypatch.setattr(trailers, "_youtube_page_search", lambda query, limit: [])
    yield
    trailers.clear_caches()


def fake_http(routes):
    """_get_json replacement serving canned payloads by URL suffix."""
    def get(url, params=None, timeout=6):
        for suffix, payload in routes.items():
            if url.endswith(suffix):
                return payload
        return {}
    return get


def tmdb_video(key, vtype="Trailer", name="Official Trailer", lang="en", official=True, site="YouTube"):
    return {"key": key, "type": vtype, "name": name, "iso_639_1": lang, "official": official, "site": site}


# ── TMDB ───────────────────────────────────────────────────


def test_tmdb_videos_ranks_trailers_first_and_drops_unplayable():
    details = {
        "original_language": "te",
        "videos": {"results": [
            tmdb_video("clip0000001", "Clip", "Scene"),
            tmdb_video("vimeo000001", site="Vimeo"),
            tmdb_video("short000001", name="Trailer #shorts"),
            tmdb_video("teaser00001", "Teaser", "Glimpse"),
            tmdb_video("trailerde01", lang="de"),
            tmdb_video("trailerte01", lang="te", official=False),
            tmdb_video("trailer0001"),
        ]},
    }
    keys = [v["key"] for v in trailers.tmdb_videos(details)]
    assert keys == ["trailer0001", "trailerte01", "trailerde01", "teaser00001", "clip0000001"]


def test_tmdb_anime_resolves_as_tv(monkeypatch):
    # Catalogue anime from TMDB are TV shows; /movie/<id> is a different title or a 404.
    monkeypatch.setattr(trailers, "_get_json", fake_http({
        "/movie/88803": {},
        "/tv/88803": {"id": 88803, "name": "Vinland Saga", "videos": {"results": [tmdb_video("vinland0001")]}},
    }))
    bundle = trailers.resolve_media("tmdb_88803", "anime", title="Vinland Saga")
    assert bundle["tmdb_kind"] == "tv"
    assert [v["key"] for v in bundle["trailers"]] == ["vinland0001"]


def test_tmdb_prefers_the_kind_whose_title_matches(monkeypatch):
    monkeypatch.setattr(trailers, "_get_json", fake_http({
        "/movie/1399": {"id": 1399, "title": "Some Movie", "videos": {"results": [tmdb_video("wrongmovie1")]}},
        "/tv/1399": {"id": 1399, "name": "Game of Thrones", "videos": {"results": [tmdb_video("gotrailer01")]}},
    }))
    bundle = trailers.resolve_media("tmdb_1399", "movie", title="Game of Thrones")
    assert bundle["tmdb_kind"] == "tv"
    assert bundle["trailers"][0]["key"] == "gotrailer01"


def test_tv_show_without_videos_uses_season_videos(monkeypatch):
    monkeypatch.setattr(trailers, "_get_json", fake_http({
        "/tv/500": {
            "id": 500, "name": "Show", "videos": {"results": []},
            "seasons": [{"season_number": 0}, {"season_number": 1}, {"season_number": 2}],
        },
        "/tv/500/season/1/videos": {"results": [tmdb_video("season10001", name="Season 1 Trailer")]},
        "/tv/500/season/2/videos": {"results": [tmdb_video("season20001", name="Season 2 Trailer")]},
    }))
    keys = [v["key"] for v in trailers.resolve_media("tmdb_500", "tv", title="Show")["trailers"]]
    assert keys == ["season10001", "season20001"]


# ── TVmaze → TMDB ──────────────────────────────────────────


def test_tvmaze_show_gets_tmdb_trailer_via_imdb_id(monkeypatch):
    monkeypatch.setattr(trailers, "_get_json", fake_http({
        "/shows/2": {"id": 2, "name": "Person of Interest", "premiered": "2011-09-22",
                     "externals": {"imdb": "tt1839578", "thetvdb": 248742}},
        "/find/tt1839578": {"tv_results": [{"id": 1411}]},
        "/tv/1411": {"id": 1411, "name": "Person of Interest", "backdrop_path": "/poi.jpg",
                     "videos": {"results": [tmdb_video("poitrailer1")]}},
    }))
    bundle = trailers.resolve_media("tvmaze_2", "tv", title="Person of Interest")
    assert (bundle["tmdb_kind"], bundle["tmdb_id"]) == ("tv", 1411)
    assert bundle["trailers"][0]["key"] == "poitrailer1"
    assert bundle["tmdb"]["backdrop_path"] == "/poi.jpg"


# ── Jikan ──────────────────────────────────────────────────


def test_youtube_id_from_jikan_embed_url():
    trailer = {"youtube_id": None, "embed_url": "https://www.youtube-nocookie.com/embed/qgQ1q2wN5yo?enablejsapi=1"}
    assert trailers.youtube_id_from(trailer) == "qgQ1q2wN5yo"
    assert trailers.youtube_id_from({"youtube_id": "abcdefghijk"}) == "abcdefghijk"
    assert trailers.youtube_id_from(None) is None


def test_jikan_trailer_promos_and_openings(monkeypatch):
    monkeypatch.setattr(trailers, "_get_json", fake_http({
        "/anime/52991/videos": {"data": {
            "promo": [
                {"title": "Teaser PV", "trailer": {"embed_url": "https://www.youtube.com/embed/teaserpv001"}},
                {"title": "CM", "trailer": {"youtube_id": "commercial1"}},
                {"title": "PV 2", "trailer": {"youtube_id": "mainpv00002"}},
            ],
            "music_videos": [{"title": "Opening", "video": {"youtube_id": "opening0001"}}],
        }},
    }))
    full = {"trailer": {"youtube_id": None, "url": "https://www.youtube.com/watch?v=official001"}}
    videos = trailers.jikan_videos("52991", full)
    assert [(v["key"], v["type"]) for v in videos] == [
        ("official001", "Trailer"),
        ("mainpv00002", "Trailer"),
        ("teaserpv001", "Teaser"),
        ("commercial1", "Clip"),
        ("opening0001", "Opening Credits"),
    ]


# ── YouTube fallback ───────────────────────────────────────


def test_parse_youtube_results_page():
    data = {"contents": {"sectionList": [
        {"adSlotRenderer": {"videoId": "advert00001"}},
        {"videoRenderer": {"videoId": "result00001", "title": {"runs": [{"text": "Arrow "}, {"text": "Trailer"}]},
                           "lengthText": {"simpleText": "2:31"}}},
        {"reelItemRenderer": {"videoId": "shortreel01"}},
        {"videoRenderer": {"videoId": "result00002", "title": {"runs": [{"text": "Arrow Season 8"}]},
                           "lengthText": {"simpleText": "1:02:03"}}},
    ]}}
    page = f"<script>var ytInitialData = {json.dumps(data)};</script>"
    assert trailers.parse_youtube_results(page) == [
        ("result00001", "Arrow Trailer", 151),
        ("result00002", "Arrow Season 8", 3723),
    ]


def test_title_overlap():
    assert trailers.title_overlap("The Odyssey", "The Odyssey | Official Trailer")
    assert trailers.title_overlap("Re:ZERO", "Re:ZERO Season 4 - Official Trailer")
    assert not trailers.title_overlap("Person of Interest", "Interstellar Official Trailer")


def test_core_titles():
    assert trailers.core_titles("Re:ZERO -Starting Life in Another World- Season 4") == [
        "Re:ZERO -Starting Life in Another World- Season 4",
        "Re:ZERO -Starting Life in Another World",
        "Re:ZERO",
    ]
    assert trailers.core_titles("Cars2") == ["Cars2"]
    assert trailers.core_titles("Kino's Journey -the Beautiful World- the Animated Series")[-1] == "Kino's Journey"


def test_youtube_fallback_when_no_source_has_videos(monkeypatch):
    hits = [
        ("fullmovie01", "Obscure Film full movie", 5400),
        ("unrelated01", "Totally Different Trailer", 120),
        ("featurett01", "Obscure Film - behind the scenes", 300),
        ("trailer0001", "Obscure Film (1999) Official Trailer", 140),
    ]
    monkeypatch.setattr(trailers, "_youtube_page_search", lambda query, limit: hits)
    videos = trailers.resolve_media("tmdb_42", "movie", title="Obscure Film", year="1999")["trailers"]
    assert [v["key"] for v in videos] == ["trailer0001", "featurett01"]
    assert all(v["source"] == "youtube" for v in videos)


def test_youtube_data_api_used_when_key_set(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "yt-key")
    monkeypatch.setattr(trailers, "_get_json", fake_http({
        "/youtube/v3/search": {"items": [{"id": {"videoId": "apitrailer1"},
                                          "snippet": {"title": "Obscure Film &amp; Co | Trailer"}}]},
    }))
    videos = trailers.youtube_trailers("Obscure Film & Co")
    assert [(v["key"], v["name"]) for v in videos] == [("apitrailer1", "Obscure Film & Co | Trailer")]


# ── API ────────────────────────────────────────────────────


def test_api_trailers_endpoint(monkeypatch):
    monkeypatch.setattr(trailers, "_get_json", fake_http({
        "/tv/94997": {"id": 94997, "name": "House of the Dragon", "videos": {"results": [tmdb_video("hotdtrailer")]}},
    }))
    resp = client.get("/api/trailers/tmdb_94997?type=tv")
    assert resp.status_code == 200
    body = resp.json()
    assert body["media_type"] == "tv"
    assert body["trailers"][0]["key"] == "hotdtrailer"


def test_api_trailers_are_cached(monkeypatch):
    calls = []

    def get(url, params=None, timeout=6):
        calls.append(url)
        return {"id": 7, "title": "Seven", "videos": {"results": [tmdb_video("seventrail1")]}} if url.endswith("/movie/7") else {}

    monkeypatch.setattr(trailers, "_get_json", get)
    for _ in range(3):
        assert client.get("/api/trailers/tmdb_7?type=movie").json()["trailers"][0]["key"] == "seventrail1"
    assert calls.count(f"{trailers.TMDB_BASE}/movie/7") == 1
