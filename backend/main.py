import pickle
import numpy as np
import faiss
import requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os

app = FastAPI(title="Movie Recommender API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load Data ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
movies = pickle.load(open(os.path.join(BASE_DIR, "movies.pkl"), "rb"))
index = faiss.read_index(os.path.join(BASE_DIR, "movies.index"))

TMDB_API_KEY = "10e0997eacd8c14e60ef40b8a46f695b"
TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
PLACEHOLDER_POSTER = "https://via.placeholder.com/500x750?text=No+Poster"


# ── Helpers ────────────────────────────────────────────────
def _fetch_tmdb(tmdb_id: int):
    """Fetch full movie details from TMDB including poster, backdrop, trailers."""
    try:
        url = f"{TMDB_BASE}/movie/{tmdb_id}?api_key={TMDB_API_KEY}&language=en-US&append_to_response=videos,credits"
        data = requests.get(url, timeout=8).json()
        return data
    except Exception:
        return {}


def _poster_url(tmdb_data: dict) -> str:
    path = tmdb_data.get("poster_path")
    return f"{POSTER_BASE}{path}" if path else PLACEHOLDER_POSTER


def _backdrop_url(tmdb_data: dict) -> str:
    path = tmdb_data.get("backdrop_path")
    return f"https://image.tmdb.org/t/p/original{path}" if path else ""


def _get_trailers(tmdb_data: dict) -> list:
    videos = tmdb_data.get("videos", {}).get("results", [])
    trailers = [
        {
            "name": v["name"],
            "key": v["key"],
            "site": v["site"],
            "type": v["type"],
        }
        for v in videos
        if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser")
    ]
    return trailers


def _get_cast_from_tmdb(tmdb_data: dict, limit: int = 10) -> list:
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


def _movie_to_dict(row, tmdb_data: dict = None) -> dict:
    """Convert a DataFrame row + optional TMDB data into a JSON-friendly dict."""
    if tmdb_data is None:
        tmdb_data = _fetch_tmdb(int(row["id"]))

    return {
        "id": int(row["id"]),
        "title": row["title"],
        "overview": row.get("overview", tmdb_data.get("overview", "")),
        "genres": row.get("genres_display", ""),
        "cast": row.get("cast_display", ""),
        "rating": float(row.get("vote_average", 0)),
        "poster": _poster_url(tmdb_data),
        "backdrop": _backdrop_url(tmdb_data),
        "release_date": tmdb_data.get("release_date", ""),
        "runtime": tmdb_data.get("runtime", 0),
        "tagline": tmdb_data.get("tagline", ""),
        "trailers": _get_trailers(tmdb_data),
        "cast_details": _get_cast_from_tmdb(tmdb_data),
    }


def _recommend_by_index(movie_idx: int, n: int = 10):
    query_vector = index.reconstruct(int(movie_idx))
    query_vector = np.array([query_vector])
    distances, indices = index.search(query_vector, n + 1)
    results = []
    for rank, i in enumerate(indices[0]):
        if i == movie_idx:
            continue
        row = movies.iloc[i]
        tmdb_data = _fetch_tmdb(int(row["id"]))
        results.append(_movie_to_dict(row, tmdb_data))
        if len(results) >= n:
            break
    return results


# ── Routes ─────────────────────────────────────────────────
@app.get("/api/movies")
def list_movies(q: Optional[str] = Query(None, min_length=1), limit: int = 20):
    """Search / list movies by title substring."""
    if q:
        mask = movies["title"].str.contains(q, case=False, na=False)
        subset = movies[mask].head(limit)
    else:
        subset = movies.head(limit)

    results = []
    for _, row in subset.iterrows():
        tmdb_data = _fetch_tmdb(int(row["id"]))
        results.append(_movie_to_dict(row, tmdb_data))
    return results


@app.get("/api/movies/titles")
def movie_titles(q: Optional[str] = Query(None)):
    """Return a lightweight list of titles for the search autocomplete."""
    if q:
        mask = movies["title"].str.contains(q, case=False, na=False)
        subset = movies[mask].head(30)
    else:
        subset = movies.head(30)
    return [{"id": int(row["id"]), "title": row["title"]} for _, row in subset.iterrows()]


@app.get("/api/movie/{tmdb_id}")
def movie_detail(tmdb_id: int):
    """Get full details for a single movie."""
    match = movies[movies["id"] == tmdb_id]
    if match.empty:
        return {"error": "Movie not found"}
    row = match.iloc[0]
    tmdb_data = _fetch_tmdb(tmdb_id)
    detail = _movie_to_dict(row, tmdb_data)
    return detail


@app.get("/api/recommend/{tmdb_id}")
def recommend(tmdb_id: int, n: int = 10):
    """Get n movie recommendations based on semantic similarity."""
    match = movies[movies["id"] == tmdb_id]
    if match.empty:
        return {"error": "Movie not found"}
    movie_idx = match.index[0]
    return _recommend_by_index(movie_idx, n)


@app.get("/api/cast/{person_id}/movies")
def cast_movies(person_id: int):
    """Fetch all movies a cast member has appeared in via TMDB."""
    try:
        url = f"{TMDB_BASE}/person/{person_id}/movie_credits?api_key={TMDB_API_KEY}&language=en-US"
        data = requests.get(url, timeout=8).json()
        cast_list = data.get("cast", [])
        # Sort by popularity
        cast_list.sort(key=lambda x: x.get("popularity", 0), reverse=True)
        results = []
        for m in cast_list[:20]:
            poster = f"{POSTER_BASE}{m['poster_path']}" if m.get("poster_path") else PLACEHOLDER_POSTER
            results.append({
                "id": m["id"],
                "title": m.get("title", "Unknown"),
                "poster": poster,
                "rating": m.get("vote_average", 0),
                "release_date": m.get("release_date", ""),
                "character": m.get("character", ""),
            })
        # Also get person details
        person_url = f"{TMDB_BASE}/person/{person_id}?api_key={TMDB_API_KEY}&language=en-US"
        person_data = requests.get(person_url, timeout=8).json()
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
