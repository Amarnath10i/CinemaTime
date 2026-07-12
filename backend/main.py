import pickle
import numpy as np
import faiss
import requests
import urllib3
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import pandas as pd

# Disable SSL warnings (needed when VPN causes cert issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="CinemaTime API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    movies = pickle.load(open(os.path.join(BASE_DIR, "movies.pkl"), "rb"))
    index = faiss.read_index(os.path.join(BASE_DIR, "movies.index"))
    DATA_LOADED = True
    LOAD_ERROR = None
    print(f"✅ Data loaded successfully! {len(movies)} movies in database.")
except Exception as e:
    import traceback
    LOAD_ERROR = traceback.format_exc()
    print(f"❌ ERROR loading data: {LOAD_ERROR}")
    movies = pd.DataFrame()
    index = None
    DATA_LOADED = False

TMDB_API_KEY = "10e0997eacd8c14e60ef40b8a46f695b"
TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
PLACEHOLDER = "https://via.placeholder.com/500x750?text=No+Poster"


@app.get("/")
def root():
    return {"status": "ok", "data_loaded": DATA_LOADED, "movie_count": len(movies), "error": LOAD_ERROR}


def safe_get(row, col, default=""):
    try:
        val = row[col]
        if pd.isna(val):
            return default
        return val
    except Exception:
        return default


def tmdb_fetch(tmdb_id, media_type="movie"):
    mt = "movie" if media_type in ("movie", "") else "tv"
    try:
        url = f"{TMDB_BASE}/{mt}/{tmdb_id}?api_key={TMDB_API_KEY}&language=en-US&append_to_response=videos,credits"
        return requests.get(url, timeout=10, verify=False).json()
    except Exception:
        return {}


def get_poster(row, tmdb_data=None):
    pp = ""
    try:
        pp = row.get("poster_path", "") if hasattr(row, "get") else getattr(row, "poster_path", "")
    except Exception:
        pass
    if pp:
        return f"{POSTER_BASE}{pp}"
    if tmdb_data and tmdb_data.get("poster_path"):
        return f"{POSTER_BASE}{tmdb_data['poster_path']}"
    return PLACEHOLDER


def get_backdrop(row, tmdb_data=None):
    bp = ""
    try:
        bp = row.get("backdrop_path", "") if hasattr(row, "get") else getattr(row, "backdrop_path", "")
    except Exception:
        pass
    if bp:
        return f"https://image.tmdb.org/t/p/original{bp}"
    if tmdb_data and tmdb_data.get("backdrop_path"):
        return f"https://image.tmdb.org/t/p/original{tmdb_data['backdrop_path']}"
    return ""


def get_trailers(tmdb_data):
    videos = tmdb_data.get("videos", {}).get("results", [])
    trailers = []
    for v in videos:
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            name_lower = v.get("name", "").lower()
            if any(word in name_lower for word in ["short", "vertical", "glimpse", "glimps", "tiktok", "reel", "teaser", "promo", "preview"]):
                continue
            trailers.append({"name": v["name"], "key": v["key"], "site": v["site"], "type": v["type"]})
    return trailers

def get_cast(tmdb_data, limit=10):
    cast = tmdb_data.get("credits", {}).get("cast", [])
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "character": c.get("character", ""),
            "profile_path": f"https://image.tmdb.org/t/p/w185{c['profile_path']}" if c.get("profile_path") else "",
        }
        for c in cast[:limit]
    ]


def row_to_dict(row, tmdb_data=None, full=False):
    tmdb_id = int(getattr(row, "id", 0))
    media_type = getattr(row, "media_type", "movie") if hasattr(row, "media_type") else "movie"

    if full and tmdb_data is None:
        tmdb_data = tmdb_fetch(tmdb_id, media_type)
    if tmdb_data is None:
        tmdb_data = {}

    return {
        "id": tmdb_id,
        "title": getattr(row, "title", ""),
        "overview": getattr(row, "overview", tmdb_data.get("overview", "")),
        "genres": getattr(row, "genres_display", "") if hasattr(row, "genres_display") else "",
        "cast": getattr(row, "cast_display", "") if hasattr(row, "cast_display") else "",
        "rating": float(getattr(row, "vote_average", 0)),
        "poster": get_poster(row, tmdb_data),
        "backdrop": get_backdrop(row, tmdb_data),
        "release_date": getattr(row, "release_date", tmdb_data.get("release_date", "")) if hasattr(row, "release_date") else tmdb_data.get("release_date", ""),
        "runtime": tmdb_data.get("runtime", 0),
        "tagline": tmdb_data.get("tagline", ""),
        "media_type": media_type,
        "trailers": get_trailers(tmdb_data) if full else [],
        "cast_details": get_cast(tmdb_data) if full else [],
    }


# ── Routes ─────────────────────────────────────────────────

@app.get("/api/movies/category/{genre}")
def movie_category(genre: str, n: int = 20, media_type: Optional[str] = Query(None)):
    if "genres_display" in movies.columns:
        mask = movies["genres_display"].str.contains(genre, case=False, na=False)
    elif "genres" in movies.columns:
        mask = movies["genres"].str.contains(genre, case=False, na=False)
    else:
        return []
    
    filtered = movies[mask]
    if media_type and media_type != "all" and "media_type" in filtered.columns:
        filtered = filtered[filtered["media_type"] == media_type]
        
    subset = filtered.head(n)
    results = []
    for _, row in subset.iterrows():
        results.append(row_to_dict(row))
    return results


@app.get("/api/movies/titles")
def movie_titles(q: Optional[str] = Query(None)):
    if q:
        mask = movies["title"].str.contains(q, case=False, na=False)
        subset = movies[mask].head(30)
    else:
        subset = movies.head(30)
    results = []
    for _, row in subset.iterrows():
        mt = row.get("media_type") if "media_type" in movies.columns else "movie"
        results.append({"id": int(row["id"]), "title": row["title"], "media_type": mt})
    return results


@app.get("/api/movie/{tmdb_id}")
def movie_detail(tmdb_id: int):
    match = movies[movies["id"] == tmdb_id]
    
    if match.empty:
        # Movie not in local DB — fetch live from TMDB
        tmdb_data = tmdb_fetch(tmdb_id, "movie")
        if not tmdb_data or "id" not in tmdb_data:
            tmdb_data = tmdb_fetch(tmdb_id, "tv")
            if not tmdb_data or "id" not in tmdb_data:
                return {"error": "Not found"}
        
        mt = "tv" if "first_air_date" in tmdb_data else "movie"
        title = tmdb_data.get("title", tmdb_data.get("name", ""))
        poster_path = tmdb_data.get("poster_path", "")
        backdrop_path = tmdb_data.get("backdrop_path", "")
        genres_list = tmdb_data.get("genres", [])
        genres_str = ", ".join([g["name"] for g in genres_list])
        
        return {
            "id": tmdb_id,
            "title": title,
            "overview": tmdb_data.get("overview", ""),
            "genres": genres_str,
            "cast": "",
            "rating": tmdb_data.get("vote_average", 0),
            "poster": f"{POSTER_BASE}{poster_path}" if poster_path else PLACEHOLDER,
            "backdrop": f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else "",
            "release_date": tmdb_data.get("release_date", tmdb_data.get("first_air_date", "")),
            "runtime": tmdb_data.get("runtime", tmdb_data.get("episode_run_time", [0])[0] if tmdb_data.get("episode_run_time") else 0),
            "tagline": tmdb_data.get("tagline", ""),
            "media_type": mt,
            "trailers": get_trailers(tmdb_data),
            "cast_details": get_cast(tmdb_data),
        }
        
    row = match.iloc[0]
    media_type = row.get("media_type") if "media_type" in movies.columns else "movie"
    tmdb_data = tmdb_fetch(tmdb_id, media_type)
    return row_to_dict(row, tmdb_data, full=True)


@app.get("/api/recommend/{tmdb_id}")
def recommend(tmdb_id: int, n: int = 10):
    match = movies[movies["id"] == tmdb_id]
    if match.empty:
        # If movie isn't in local DB, we can't do FAISS search
        return []
        
    movie_idx = match.index[0]
    query_vector = index.reconstruct(int(movie_idx))
    query_vector = np.array([query_vector])
    distances, indices = index.search(query_vector, n + 1)
    results = []
    for i in indices[0]:
        if i == movie_idx:
            continue
        row = movies.iloc[i]
        results.append(row_to_dict(row))
        if len(results) >= n:
            break
    return results


@app.get("/api/cast/{person_id}/movies")
def cast_movies(person_id: int):
    try:
        url = f"{TMDB_BASE}/person/{person_id}/combined_credits?api_key={TMDB_API_KEY}&language=en-US"
        data = requests.get(url, timeout=10, verify=False).json()
        cast_list = data.get("cast", [])
        cast_list.sort(key=lambda x: x.get("popularity", 0), reverse=True)
        results = []
        for m in cast_list[:24]:
            poster = f"{POSTER_BASE}{m['poster_path']}" if m.get("poster_path") else PLACEHOLDER
            results.append({
                "id": m["id"],
                "title": m.get("title", m.get("name", "Unknown")),
                "poster": poster,
                "rating": m.get("vote_average", 0),
                "release_date": m.get("release_date", m.get("first_air_date", "")),
                "character": m.get("character", ""),
                "media_type": m.get("media_type", "movie"),
            })
        person_url = f"{TMDB_BASE}/person/{person_id}?api_key={TMDB_API_KEY}&language=en-US"
        person_data = requests.get(person_url, timeout=10, verify=False).json()
        person_info = {
            "name": person_data.get("name", ""),
            "biography": person_data.get("biography", ""),
            "profile_path": f"https://image.tmdb.org/t/p/w300{person_data['profile_path']}" if person_data.get("profile_path") else "",
            "birthday": person_data.get("birthday", ""),
            "place_of_birth": person_data.get("place_of_birth", ""),
        }
        return {"person": person_info, "movies": results}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/trending")
def trending():
    try:
        url = f"{TMDB_BASE}/trending/all/week?api_key={TMDB_API_KEY}&language=en-US"
        data = requests.get(url, timeout=5, verify=False).json()
        if "results" not in data or not data["results"]:
            raise ValueError("No results from TMDB")
        results = []
        for r in data.get("results", [])[:20]:
            poster = f"{POSTER_BASE}{r['poster_path']}" if r.get("poster_path") else PLACEHOLDER
            backdrop = f"https://image.tmdb.org/t/p/original{r['backdrop_path']}" if r.get("backdrop_path") else ""
            results.append({
                "id": r["id"],
                "title": r.get("title", r.get("name", "Unknown")),
                "poster": poster,
                "backdrop": backdrop,
                "overview": r.get("overview", ""),
                "rating": r.get("vote_average", 0),
                "release_date": r.get("release_date", r.get("first_air_date", "")),
                "media_type": r.get("media_type", "movie"),
            })
        return results
    except Exception as e:
        # Fallback to local most popular movies if TMDB Live Trending is rate limited or blocked
        subset = movies.head(20)
        results = []
        for _, row in subset.iterrows():
            results.append(row_to_dict(row))
        return results
