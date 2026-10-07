"""
Trailer, teaser and promo lookup for every title in the catalogue.

Each title is tried against these sources, in order:
  1. TMDB videos, in English plus the title's original language. TV shows
     with nothing at the show level fall back to their seasons' videos.
  2. Jikan (MyAnimeList): the anime's trailer, its promos/PVs/CMs, and its
     opening/ending videos.
  3. TMDB again, through a cross-reference: TVmaze shows by IMDb/TheTVDB id,
     Jikan anime by title search.
  4. YouTube search, so even obscure titles get something to play: the
     YouTube Data API when YOUTUBE_API_KEY is set, otherwise the public
     results page.

Results are cached in memory, so the hero carousel and detail page can ask
repeatedly without hammering the upstream APIs.
"""
import html
import json
import math
import os
import re
import threading
import time
from collections import OrderedDict
from urllib.parse import urlparse

import requests

TMDB_BASE = "https://api.themoviedb.org/3"
JIKAN_BASE = "https://api.jikan.moe/v4"
TVMAZE_BASE = "https://api.tvmaze.com"
# Jikan answers in well under a second when healthy; when it is down, fail fast
# and fall back to TMDB rather than stalling the page.
JIKAN_TIMEOUT = 3

# TMDB filters videos to the request language unless told otherwise. Ask for
# English, language-less uploads, and the original languages most titles in
# the catalogue use (Indian, East Asian and European).
VIDEO_LANGUAGES = "en,null,hi,ta,te,ml,kn,bn,mr,pa,ja,ko,zh,cn,es,fr,de,it,pt,ru,tr,th,id"

# Lower index plays first.
VIDEO_TYPE_ORDER = ["Trailer", "Teaser", "Clip", "Featurette", "Opening Credits", "Behind the Scenes", "Bloopers"]
MAX_VIDEOS = 20
MAX_YOUTUBE_RESULTS = 3

# Vertical clips look broken in a 16:9 player.
_VERTICAL = re.compile(r"#shorts|\bshorts\b|vertical|tiktok|\breels?\b")
_TRAILER_WORDS = re.compile(r"trailer|teaser|promo|\bpv\b|glimpse|first look|sneak peek|preview")
_YOUTUBE_ID_IN_URL = re.compile(r"(?:embed/|v=|youtu\.be/)([\w-]{11})")
_SEASON_SUFFIX = re.compile(
    r"\s*[:\-–]?\s*\b(?:season\s*\d+|\d+(?:st|nd|rd|th)\s+season|part\s*\d+|cour\s*\d+|s\d+|final season)\b.*$",
    re.IGNORECASE,
)
_TITLE_STOPWORDS = {"the", "a", "an", "of", "and", "to", "in", "on", "no", "wa", "ga", "season", "part"}

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

_session = requests.Session()
_session.headers["User-Agent"] = "CinemaTime/1.0 (+https://cinema-time-black.vercel.app)"


def _ssl_verify():
    return os.getenv("DISABLE_SSL_VERIFY", "").lower() != "true"


def _tmdb_key():
    return os.getenv("TMDB_API_KEY") or ""


# ── Caching ────────────────────────────────────────────────


class _TTLCache:
    """Small thread-safe LRU cache whose entries expire."""

    def __init__(self, maxsize):
        self._items = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            hit = self._items.get(key)
            if hit is None:
                return None
            expires, value = hit
            if expires < time.time():
                del self._items[key]
                return None
            self._items.move_to_end(key)
            return value

    def set(self, key, value, ttl):
        with self._lock:
            self._items[key] = (time.time() + ttl, value)
            self._items.move_to_end(key)
            while len(self._items) > self._maxsize:
                self._items.popitem(last=False)

    def clear(self):
        with self._lock:
            self._items.clear()


_trailer_cache = _TTLCache(maxsize=8000)
_details_cache = _TTLCache(maxsize=300)
_ref_cache = _TTLCache(maxsize=8000)

HOUR = 3600
TRAILERS_TTL = 12 * HOUR
EMPTY_TTL = HOUR // 2

# Hosts that recently timed out are skipped for a while, so one unreachable
# API (Jikan is blocked on some networks) doesn't stall every request.
_host_down_until = {}
HOST_COOLDOWN = 120


def clear_caches():
    for cache in (_trailer_cache, _details_cache, _ref_cache):
        cache.clear()
    _host_down_until.clear()


# ── HTTP ───────────────────────────────────────────────────


def _get_json(url, params=None, timeout=6):
    """GET a JSON object, returning {} on any failure or non-object body."""
    host = urlparse(url).netloc
    if _host_down_until.get(host, 0) > time.time():
        return {}
    try:
        resp = _session.get(url, params=params, timeout=timeout, verify=_ssl_verify())
    except (requests.ConnectionError, requests.Timeout):
        _host_down_until[host] = time.time() + HOST_COOLDOWN
        return {}
    except requests.RequestException:
        return {}
    if resp.status_code != 200:
        return {}
    try:
        body = resp.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


# ── Helpers ────────────────────────────────────────────────


def _video(key, name, vtype, source, official=False):
    return {
        "key": key,
        "name": name or vtype,
        "site": "YouTube",
        "type": vtype,
        "source": source,
        "official": bool(official),
    }


def _dedupe(videos, limit=MAX_VIDEOS):
    seen, out = set(), []
    for v in videos:
        if not v.get("key") or v["key"] in seen:
            continue
        seen.add(v["key"])
        out.append(v)
    return out[:limit]


def _norm_title(text):
    return re.sub(r"[^\w]+", " ", str(text or "").lower()).strip()


def titles_match(a, b):
    a, b = _norm_title(a), _norm_title(b)
    return bool(a and b) and (a == b or a in b or b in a)


def core_titles(title):
    """The title plus its shorter forms: without a season suffix, and without a subtitle.

    "Re:ZERO -Starting Life in Another World- Season 4" also yields
    "Re:ZERO -Starting Life in Another World-" and "Re:ZERO", which is how
    uploads tend to name it.
    """
    names = [title, _SEASON_SUFFIX.sub("", title).strip()]
    names.append(re.split(r"\s+[-–(]|:\s", names[-1])[0].strip())
    return [n for n in dict.fromkeys(names) if n]


def title_overlap(item_title, video_title):
    """True when a YouTube result's title plausibly refers to the item."""
    tokens = [t for t in _norm_title(item_title).split() if len(t) > 1 and t not in _TITLE_STOPWORDS]
    words = set(_norm_title(video_title).split())
    if not tokens:
        return _norm_title(item_title) in _norm_title(video_title)
    hits = sum(1 for t in tokens if t in words)
    return hits >= max(1, math.ceil(len(tokens) * 0.6))


def _year(value):
    match = re.match(r"(\d{4})", str(value or ""))
    return match.group(1) if match else ""


def _classify(name):
    lowered = (name or "").lower()
    if re.search(r"teaser|glimpse|first look|sneak peek", lowered):
        return "Teaser"
    if re.search(r"\bcm\b|commercial|\bspot\b", lowered):
        return "Clip"
    return "Trailer"


# ── TMDB ───────────────────────────────────────────────────


def tmdb_videos(details):
    """Playable YouTube videos from a TMDB payload, best first."""
    original = details.get("original_language")
    results = (details.get("videos") or {}).get("results") or []
    ranked = []
    for pos, v in enumerate(results):
        vtype = v.get("type")
        if v.get("site") != "YouTube" or not v.get("key") or vtype not in VIDEO_TYPE_ORDER:
            continue
        if _VERTICAL.search((v.get("name") or "").lower()):
            continue
        lang_rank = 0 if v.get("iso_639_1") in ("en", original, None) else 1
        rank = (VIDEO_TYPE_ORDER.index(vtype), lang_rank, not v.get("official"), pos)
        ranked.append((rank, _video(v["key"], v.get("name"), vtype, "tmdb", v.get("official"))))
    ranked.sort(key=lambda pair: pair[0])
    return [video for _, video in ranked]


def fetch_tmdb(kind, tmdb_id):
    """TMDB movie/tv details with videos, credits and external ids."""
    key = _tmdb_key()
    if not key or kind not in ("movie", "tv") or not tmdb_id:
        return {}
    cache_key = (kind, str(tmdb_id))
    cached = _details_cache.get(cache_key)
    if cached is not None:
        return cached
    data = _get_json(
        f"{TMDB_BASE}/{kind}/{tmdb_id}",
        {
            "api_key": key,
            "language": "en-US",
            "append_to_response": "videos,credits,external_ids",
            "include_video_language": VIDEO_LANGUAGES,
        },
    )
    if not isinstance(data, dict) or not data.get("id"):
        data = {}
    _details_cache.set(cache_key, data, 6 * HOUR if data else EMPTY_TTL)
    return data


def fetch_tmdb_title(tmdb_id, kinds, expected_title=""):
    """Fetch a TMDB id whose movie/tv kind is uncertain.

    Movie and TV ids share a number space, so tmdb_1399 can be a movie and a
    show at once; when we know the title, prefer the kind whose name matches.
    Returns (kind, details) or (None, {}).
    """
    fallback = (None, {})
    for kind in kinds:
        data = fetch_tmdb(kind, tmdb_id)
        if not data:
            continue
        names = (data.get("title"), data.get("name"), data.get("original_title"), data.get("original_name"))
        if not expected_title or any(titles_match(expected_title, n) for n in names if n):
            return kind, data
        if fallback[0] is None:
            fallback = (kind, data)
    return fallback


def tmdb_season_videos(tv_id, details):
    """Videos from a show's first and latest seasons, for shows with none at the top level."""
    key = _tmdb_key()
    seasons = sorted(
        (s for s in details.get("seasons") or [] if (s.get("season_number") or 0) > 0),
        key=lambda s: s["season_number"],
    )
    picks = [seasons[0], seasons[-1]] if len(seasons) > 1 else seasons
    videos = []
    for season in picks:
        data = _get_json(
            f"{TMDB_BASE}/tv/{tv_id}/season/{season['season_number']}/videos",
            {"api_key": key, "include_video_language": VIDEO_LANGUAGES},
        )
        videos += tmdb_videos({"videos": data, "original_language": details.get("original_language")})
    return videos


def tmdb_find(external_id, source):
    """Look a title up on TMDB by an IMDb ('imdb_id') or TheTVDB ('tvdb_id') id."""
    if not external_id or not _tmdb_key():
        return None, None
    data = _get_json(f"{TMDB_BASE}/find/{external_id}", {"api_key": _tmdb_key(), "external_source": source})
    for kind, field in (("tv", "tv_results"), ("movie", "movie_results")):
        results = data.get(field) or []
        if results:
            return kind, results[0]["id"]
    return None, None


def tmdb_search(titles, year="", kinds=("tv", "movie"), animation=False):
    """Find a TMDB id by title, trying each candidate title with and without the year."""
    if not _tmdb_key():
        return None, None
    for title in [t for t in dict.fromkeys(titles) if t]:
        for kind in kinds:
            for with_year in ([True, False] if year else [False]):
                params = {"api_key": _tmdb_key(), "query": title, "language": "en-US", "include_adult": "false"}
                if with_year:
                    params["first_air_date_year" if kind == "tv" else "year"] = year
                results = _get_json(f"{TMDB_BASE}/search/{kind}", params).get("results") or []
                for r in results[:5]:
                    if animation and 16 not in (r.get("genre_ids") or []):
                        continue
                    names = (r.get("name"), r.get("title"), r.get("original_name"), r.get("original_title"))
                    if any(titles_match(title, n) for n in names if n):
                        return kind, r["id"]
    return None, None


# ── Jikan (MyAnimeList) ────────────────────────────────────


def youtube_id_from(trailer):
    """YouTube id from a Jikan trailer object; Jikan often leaves youtube_id empty."""
    if not isinstance(trailer, dict):
        return None
    if trailer.get("youtube_id"):
        return trailer["youtube_id"]
    for field in ("embed_url", "url"):
        match = _YOUTUBE_ID_IN_URL.search(trailer.get(field) or "")
        if match:
            return match.group(1)
    return None


def jikan_videos(mal_id, full=None):
    """An anime's trailer, promos/PVs and opening/ending videos from Jikan."""
    videos = []
    key = youtube_id_from((full or {}).get("trailer"))
    if key:
        videos.append(_video(key, "Official Trailer", "Trailer", "jikan", True))

    data = _get_json(f"{JIKAN_BASE}/anime/{mal_id}/videos", timeout=JIKAN_TIMEOUT).get("data")
    if not isinstance(data, dict):
        return videos

    promos = []
    for promo in data.get("promo") or []:
        key = youtube_id_from(promo.get("trailer"))
        if key:
            title = promo.get("title") or "Promo"
            promos.append(_video(key, title, _classify(title), "jikan", True))
    promos.sort(key=lambda v: VIDEO_TYPE_ORDER.index(v["type"]))
    videos += promos

    for mv in data.get("music_videos") or []:
        key = youtube_id_from(mv.get("video"))
        if key:
            videos.append(_video(key, mv.get("title") or "Opening", "Opening Credits", "jikan"))
    return videos


def _anime_titles(data, title=""):
    names = [title, data.get("title_english"), data.get("title")]
    names += [t.get("title") for t in data.get("titles") or [] if t.get("type") in ("English", "Synonym")]
    variants = [v for n in names if n for v in core_titles(n)]
    # Each candidate costs up to four TMDB searches; stop at the likeliest few.
    return list(dict.fromkeys(variants))[:4]


# ── YouTube search ─────────────────────────────────────────


def _duration_seconds(text):
    try:
        parts = [int(p) for p in str(text).split(":")]
    except ValueError:
        return None
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def parse_youtube_results(page):
    """[(video_id, title, seconds)] from a YouTube results page, ads and Shorts excluded."""
    match = re.search(r"var ytInitialData = (\{.*?\});</script>", page, re.S)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except ValueError:
        return []
    found = []

    def walk(node):
        if isinstance(node, dict):
            renderer = node.get("videoRenderer")
            if isinstance(renderer, dict) and renderer.get("videoId"):
                title = "".join(run.get("text", "") for run in (renderer.get("title") or {}).get("runs", []))
                length = (renderer.get("lengthText") or {}).get("simpleText")
                found.append((renderer["videoId"], title, _duration_seconds(length) if length else None))
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return found


def _youtube_api_search(query, api_key, limit):
    data = _get_json(
        "https://www.googleapis.com/youtube/v3/search",
        {
            "part": "snippet",
            "type": "video",
            "videoEmbeddable": "true",
            "maxResults": limit,
            "q": query,
            "key": api_key,
        },
    )
    return [
        (item["id"]["videoId"], html.unescape(item["snippet"]["title"]), None)
        for item in data.get("items") or []
        if item.get("id", {}).get("videoId")
    ]


def _youtube_page_search(query, limit):
    host = "www.youtube.com"
    if _host_down_until.get(host, 0) > time.time():
        return []
    try:
        resp = _session.get(
            "https://www.youtube.com/results",
            # sp=EgIQAQ== restricts results to videos (no channels/playlists).
            params={"search_query": query, "sp": "EgIQAQ=="},
            headers={"User-Agent": _BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"},
            cookies={"CONSENT": "YES+1", "SOCS": "CAI"},
            timeout=8,
            verify=_ssl_verify(),
        )
    except (requests.ConnectionError, requests.Timeout):
        _host_down_until[host] = time.time() + HOST_COOLDOWN
        return []
    except requests.RequestException:
        return []
    if resp.status_code != 200:
        return []
    return parse_youtube_results(resp.text)[:limit]


def youtube_search(query, limit=8):
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        hits = _youtube_api_search(query, api_key, limit)
        if hits:
            return hits
    return _youtube_page_search(query, limit)


def youtube_trailers(title, year="", media_type="movie"):
    """Search YouTube for a title's trailer, keeping only results that name it."""
    if not title:
        return []
    names = core_titles(title)
    kind = "anime" if media_type == "anime" else ""
    # Search the full title first; if nothing matches, its shortest form.
    for search_title in dict.fromkeys([title, names[-1]]):
        query = " ".join(p for p in (search_title, year, kind, "official trailer") if p)
        picks = []
        for video_id, video_title, seconds in youtube_search(query):
            if seconds is not None and not 10 <= seconds <= 15 * 60:
                continue  # skips Shorts-length clips and full episodes/films
            if _VERTICAL.search(video_title.lower()):
                continue
            if not any(title_overlap(name, video_title) for name in names):
                continue
            picks.append(_video(video_id, video_title, _classify(video_title), "youtube"))
        if picks:
            picks.sort(key=lambda v: 0 if _TRAILER_WORDS.search(v["name"].lower()) else 1)
            return picks[:MAX_YOUTUBE_RESULTS]
    return []


# ── Resolution ─────────────────────────────────────────────


def _tmdb_kinds(media_type):
    # Anime from TMDB in the catalogue are almost all series.
    return ["movie", "tv"] if media_type == "movie" else ["tv", "movie"]


def resolve_media(item_id, media_type="movie", title="", year="", need_details=True):
    """Details plus every playable video for one catalogue item.

    item_id is a prefixed id: tmdb_<id>, tvmaze_<id> or jikan_<mal_id>.
    Returns a dict with:
      data       raw payload from the item's own source (TMDB, TVmaze or Jikan)
      tmdb       TMDB details for the item ({} when there is no TMDB match);
                 the same object as data for TMDB items
      tmdb_kind  "movie" / "tv" / None
      tmdb_id    TMDB id or None
      trailers   playable YouTube videos, best first
    With need_details=False the TMDB cross-reference for anime is skipped when
    Jikan already has videos; trailer-only callers don't need it.
    """
    prefix, _, raw_id = item_id.partition("_")
    data, tmdb, kind, tmdb_id = {}, {}, None, None
    videos = []
    year = _year(year)

    if prefix == "tmdb":
        kind, tmdb = fetch_tmdb_title(raw_id, _tmdb_kinds(media_type), title)
        data = tmdb
        tmdb_id = raw_id if kind else None
        title = title or tmdb.get("title") or tmdb.get("name") or ""
        year = year or _year(tmdb.get("release_date") or tmdb.get("first_air_date"))
        videos += tmdb_videos(tmdb)
        if not videos and kind == "tv":
            videos += tmdb_season_videos(raw_id, tmdb)

    elif prefix == "tvmaze":
        data = _get_json(f"{TVMAZE_BASE}/shows/{raw_id}", {"embed": "cast"})
        title = title or data.get("name") or ""
        year = year or _year(data.get("premiered"))
        kind, tmdb_id = resolve_tmdb_ref(item_id, media_type, title, year, source=data)
        tmdb = fetch_tmdb(kind, tmdb_id) if kind else {}
        videos += tmdb_videos(tmdb)
        if not videos and kind == "tv":
            videos += tmdb_season_videos(tmdb_id, tmdb)

    elif prefix == "jikan":
        full = _get_json(f"{JIKAN_BASE}/anime/{raw_id}/full", timeout=JIKAN_TIMEOUT)
        data = full.get("data") if isinstance(full.get("data"), dict) else {}
        title = title or data.get("title_english") or data.get("title") or ""
        year = year or _year(data.get("year") or (data.get("aired") or {}).get("from"))
        videos += jikan_videos(raw_id, data)
        if need_details or not videos:
            kind, tmdb_id = resolve_tmdb_ref(item_id, media_type, title, year, source=data)
            tmdb = fetch_tmdb(kind, tmdb_id) if kind else {}
            videos += tmdb_videos(tmdb)

    if not videos:
        videos = youtube_trailers(title, year, media_type)

    trailers = _dedupe(videos)
    _trailer_cache.set((item_id, media_type), trailers, TRAILERS_TTL if trailers else EMPTY_TTL)
    return {"data": data or {}, "tmdb": tmdb or {}, "tmdb_kind": kind, "tmdb_id": tmdb_id, "trailers": trailers}


def resolve_trailers(item_id, media_type="movie", title="", year=""):
    """Cached list of playable videos for one item (see resolve_media)."""
    cached = _trailer_cache.get((item_id, media_type))
    if cached is not None:
        return cached
    return resolve_media(item_id, media_type, title, year, need_details=False)["trailers"]


def resolve_tmdb_ref(item_id, media_type="movie", title="", year="", source=None):
    """(kind, tmdb_id) for any catalogue item, or (None, None) when TMDB doesn't have it."""
    cached = _ref_cache.get(item_id)
    if cached is not None:
        return cached

    prefix, _, raw_id = item_id.partition("_")
    ref = (None, None)
    if prefix == "tmdb":
        kind, _ = fetch_tmdb_title(raw_id, _tmdb_kinds(media_type), title)
        ref = (kind, raw_id) if kind else (None, None)
    elif prefix == "tvmaze":
        show = source if source is not None else _get_json(f"{TVMAZE_BASE}/shows/{raw_id}")
        externals = show.get("externals") or {}
        ref = tmdb_find(externals.get("imdb"), "imdb_id")
        if not ref[0]:
            ref = tmdb_find(externals.get("thetvdb"), "tvdb_id")
        if not ref[0]:
            ref = tmdb_search([title or show.get("name")], year or _year(show.get("premiered")), kinds=("tv",))
    elif prefix == "jikan":
        anime = source if source is not None else (_get_json(f"{JIKAN_BASE}/anime/{raw_id}", timeout=JIKAN_TIMEOUT).get("data") or {})
        kinds = ("movie", "tv") if anime.get("type") == "Movie" else ("tv", "movie")
        ref = tmdb_search(_anime_titles(anime, title), year, kinds=kinds, animation=True)

    # Don't pin a miss for a day when the cause was a missing key or an outage.
    _ref_cache.set(item_id, ref, 24 * HOUR if ref[0] else EMPTY_TTL)
    return ref
