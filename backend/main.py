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
from pydantic import BaseModel

# ── Configuration from environment ─────────────────────────
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    print(
        "⚠️ WARNING: TMDB_API_KEY environment variable is not set. "
        "Live fetches for missing data/trailers will fail. "
        "Set it in your deployment config."
    )

DISABLE_SSL_VERIFY = os.getenv("DISABLE_SSL_VERIFY", "").lower() == "true"
SSL_VERIFY = not DISABLE_SSL_VERIFY

if DISABLE_SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_default_origins = "https://cinema-time-black.vercel.app,http://localhost:3000"
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app = FastAPI(title="CinemaTime API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
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

try:
    import json
    with open(os.path.join(BASE_DIR, "clusters.json"), "r") as f:
        CLUSTERS = json.load(f)
    print(f"✅ Loaded {len(CLUSTERS)} vibe clusters.")
except Exception:
    CLUSTERS = []
    print("⚠️ No clusters.json found. Run build_dataset.py to generate vibes.")

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


def fetch_media_details(item_id: str, media_type: str = "movie"):
    """Fetch details from TMDB, TVmaze, or Jikan based on prefix."""
    if item_id.startswith("tmdb_"):
        raw_id = item_id.replace("tmdb_", "")
        url = f"{TMDB_BASE}/{media_type}/{raw_id}?api_key={TMDB_API_KEY}&append_to_response=videos,credits&language=en-US"
        try:
            return requests.get(url, timeout=5, verify=SSL_VERIFY).json()
        except:
            return {}
            
    elif item_id.startswith("tvmaze_"):
        raw_id = item_id.replace("tvmaze_", "")
        url = f"https://api.tvmaze.com/shows/{raw_id}?embed=cast"
        try:
            return requests.get(url, timeout=5).json()
        except:
            return {}
            
    elif item_id.startswith("jikan_"):
        raw_id = item_id.replace("jikan_", "")
        url = f"https://api.jikan.moe/v4/anime/{raw_id}/full"
        try:
            data = requests.get(url, timeout=5).json()
            return data.get("data", {}) if isinstance(data, dict) else {}
        except:
            return {}
            
    return {}


def get_poster(row, tmdb_data=None):
    pp = ""
    try:
        pp = row.get("poster_path", "") if hasattr(row, "get") else getattr(row, "poster_path", "")
    except Exception:
        pass
    if pp:
        return pp if pp.startswith("http") else f"{POSTER_BASE}{pp}"
    if tmdb_data and tmdb_data.get("poster_path"):
        tp = tmdb_data["poster_path"]
        return tp if tp.startswith("http") else f"{POSTER_BASE}{tp}"
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


def get_trailers(media_data):
    # Handle Jikan anime trailers
    if "trailer" in media_data and "youtube_id" in media_data["trailer"]:
        yt_id = media_data["trailer"]["youtube_id"]
        if yt_id:
            return [{"name": "Trailer", "key": yt_id, "site": "YouTube", "type": "Trailer"}]
            
    # Handle TMDB videos
    videos = media_data.get("videos", {}).get("results", [])
    trailers = []
    
    # Priority: Trailer > Teaser > Clip > Featurette
    priority = {"Trailer": 1, "Teaser": 2, "Clip": 3, "Featurette": 4}
    
    for v in videos:
        if v.get("site") == "YouTube" and v.get("type") in priority:
            name_lower = v.get("name", "").lower()
            # Still filter out vertical videos which ruin UX
            if any(word in name_lower for word in ["short", "vertical", "tiktok", "reel"]):
                continue
            trailers.append({"name": v["name"], "key": v["key"], "site": v["site"], "type": v["type"]})
            
    trailers.sort(key=lambda x: priority.get(x["type"], 99))
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
    item_id = str(getattr(row, "id", ""))
    media_type = getattr(row, "media_type", "movie") if hasattr(row, "media_type") else "movie"

    if full and tmdb_data is None:
        tmdb_data = fetch_media_details(item_id, media_type)
    if tmdb_data is None:
        tmdb_data = {}

    return {
        "id": item_id,
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
        results.append({"id": str(row["id"]), "title": row["title"], "media_type": mt})
    return results


@app.get("/api/movie/{item_id:path}")
def movie_detail(item_id: str):
    # Backward compatibility for old integer IDs hitting this route directly
    if item_id.isdigit():
        item_id = f"tmdb_{item_id}"
        
    match = movies[movies["id"] == item_id]
    
    if match.empty:
        # Movie not in local DB — fetch live
        mt_guess = "tv" if "tvmaze" in item_id else "anime" if "jikan" in item_id else "movie"
        media_data = fetch_media_details(item_id, mt_guess)
        if not media_data:
            return {"error": "Not found"}
        
        title = media_data.get("title", media_data.get("name", media_data.get("title_english", "")))
        poster_path = media_data.get("poster_path", media_data.get("image", {}).get("original", ""))
        backdrop_path = media_data.get("backdrop_path", "")
        
        genres_list = media_data.get("genres", [])
        if genres_list and isinstance(genres_list[0], dict):
            genres_str = ", ".join([g["name"] for g in genres_list])
        else:
            genres_str = ", ".join(genres_list)
        
        return {
            "id": item_id,
            "title": title,
            "overview": media_data.get("overview", media_data.get("summary", media_data.get("synopsis", ""))),
            "genres": genres_str,
            "cast": "",
            "rating": media_data.get("vote_average", media_data.get("rating", {}).get("average", media_data.get("score", 0))),
            "poster": f"{POSTER_BASE}{poster_path}" if poster_path and not poster_path.startswith("http") else poster_path or PLACEHOLDER,
            "backdrop": f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else "",
            "release_date": media_data.get("release_date", media_data.get("first_air_date", media_data.get("premiered", ""))),
            "runtime": media_data.get("runtime", 0),
            "tagline": media_data.get("tagline", ""),
            "media_type": mt_guess,
            "trailers": get_trailers(media_data),
            "cast_details": get_cast(media_data),
        }
        
    row = match.iloc[0]
    media_type = row.get("media_type") if "media_type" in movies.columns else "movie"
    media_data = fetch_media_details(item_id, media_type)
    return row_to_dict(row, media_data, full=True)


@app.get("/api/recommend/{item_id:path}")
def recommend(item_id: str, n: int = 10, diversity: float = 0.5):
    # Backward compatibility
    if item_id.isdigit():
        item_id = f"tmdb_{item_id}"
        
    match = movies[movies["id"] == item_id]
    if match.empty:
        # If movie isn't in local DB, we can't do FAISS search
        return []
        
    movie_idx = match.index[0]
    query_vector = index.reconstruct(int(movie_idx))
    query_vector = np.array([query_vector])
    
    # 1. Over-retrieve candidates
    fetch_n = min(n * 3 + 1, index.ntotal)
    distances, indices = index.search(query_vector, fetch_n)
    
    candidates = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == movie_idx:
            continue
        candidates.append((dist, idx))
        
    if not candidates:
        return []
        
    # 2. MMR Re-ranking
    selected_indices = []
    selected_vectors = []
    
    # Pre-fetch vectors for candidates to compute similarity efficiently
    candidate_vectors = {idx: index.reconstruct(int(idx)) for _, idx in candidates}
    
    while len(selected_indices) < n and candidates:
        best_score = -float('inf')
        best_candidate_pos = -1
        
        for pos, (sim_to_query, idx) in enumerate(candidates):
            if not selected_vectors:
                mmr_score = sim_to_query
            else:
                v_c = candidate_vectors[idx]
                sims_to_selected = [np.dot(v_c, v_s) for v_s in selected_vectors]
                max_sim_to_selected = max(sims_to_selected)
                mmr_score = (1.0 - diversity) * sim_to_query - diversity * max_sim_to_selected
                
            if mmr_score > best_score:
                best_score = mmr_score
                best_candidate_pos = pos
                
        # Move best candidate to selected
        sim_to_query, best_idx = candidates.pop(best_candidate_pos)
        selected_indices.append((best_idx, sim_to_query))
        selected_vectors.append(candidate_vectors[best_idx])
        
    # 3. Explanations & Formatting
    results = []
    source_row = movies.iloc[movie_idx]
    source_genres = set(g.strip() for g in source_row.get("genres_display", "").split(",") if g.strip())
    
    # Simple thematic overlap using tags (ignoring common short words)
    stop_words = {"this", "that", "with", "from", "movie", "film", "series", "about", "their", "there", "which", "anime", "when", "into", "after"}
    source_tags = set(w for w in source_row.get("tags", "").split() if len(w) > 4 and w not in stop_words)
    
    for idx, sim in selected_indices:
        row = movies.iloc[idx]
        rec_dict = row_to_dict(row)
        rec_dict["similarity_score"] = float(sim)
        
        # Explanations
        rec_genres = set(g.strip() for g in row.get("genres_display", "").split(",") if g.strip())
        shared_genres = list(source_genres.intersection(rec_genres))
        
        rec_tags = set(w for w in row.get("tags", "").split() if len(w) > 4 and w not in stop_words)
        shared_themes = list(source_tags.intersection(rec_tags))
        
        match_pct = min(100, max(0, int(sim * 100)))
        reason_parts = [f"{match_pct}% match"]
        
        if shared_themes:
            reason_parts.append(f"themes: {', '.join(shared_themes[:3])}")
        elif shared_genres:
            reason_parts.append(f"genres: {', '.join(shared_genres[:2])}")
            
        rec_dict["explanation"] = {
            "match_pct": match_pct,
            "shared_genres": shared_genres,
            "shared_themes": shared_themes,
            "reason": " — ".join(reason_parts)
        }
        
        results.append(rec_dict)
        
    return results


@app.get("/api/cast/{person_id}/movies")
def cast_movies(person_id: int):
    try:
        url = f"{TMDB_BASE}/person/{person_id}/combined_credits?api_key={TMDB_API_KEY}&language=en-US"
        data = requests.get(url, timeout=10, verify=SSL_VERIFY).json()
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
        person_data = requests.get(person_url, timeout=10, verify=SSL_VERIFY).json()
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


class ChatRequest(BaseModel):
    message: str

@app.post("/api/assistant/chat")
def assistant_chat(req: ChatRequest):
    try:
        msg = req.message.lower().strip()
        
        # 1. Try to extract a person's name
        name_to_search = ""
        keywords = ["starring", "actor", "actress", "director", "directed by", "movies by", "movies with", "with", "by"]
        
        for kw in keywords:
            if kw in msg:
                parts = msg.split(kw)
                if len(parts) > 1:
                    extracted = parts[1].strip()
                    for word in ["please", "?", ".", "movies"]:
                        extracted = extracted.replace(word, "").strip()
                    if extracted:
                        name_to_search = extracted
                        break

        # 2. If it looks like a person query, hit TMDB Person Search
        if name_to_search:
            person_url = f"{TMDB_BASE}/search/person?api_key={TMDB_API_KEY}&query={name_to_search}&language=en-US"
            person_data = requests.get(person_url, timeout=10, verify=SSL_VERIFY).json()
            
            if person_data.get("results"):
                person = person_data["results"][0]
                person_id = person["id"]
                person_name = person["name"]
                
                discover_url = f"{TMDB_BASE}/discover/movie?api_key={TMDB_API_KEY}&with_people={person_id}&sort_by=popularity.desc&language=en-US"
                discover_data = requests.get(discover_url, timeout=10, verify=SSL_VERIFY).json()
                
                results = []
                for r in discover_data.get("results", [])[:15]:
                    poster = f"{POSTER_BASE}{r['poster_path']}" if r.get("poster_path") else PLACEHOLDER
                    results.append({
                        "id": r["id"],
                        "title": r.get("title", r.get("name", "Unknown")),
                        "poster": poster,
                        "rating": r.get("vote_average", 0),
                        "media_type": "movie",
                    })
                    
                if results:
                    return {"reply": f"Here are the top movies for {person_name}:", "movies": results}

        # 3. If no person found (or no keywords), try a simple title search in our local DB
        clean_msg = msg.replace("show me", "").replace("find", "").replace("movies", "").replace("please", "").strip()
        
        if not clean_msg:
            return {"reply": "I'm your Cinema AI! You can search for movies or ask for specific actors/directors."}

        # Check local DB
        if not movies.empty:
            mask = movies["title"].str.contains(clean_msg, case=False, na=False)
            subset = movies[mask].head(15)
            if not subset.empty:
                local_results = [row_to_dict(r) for _, r in subset.iterrows()]
                return {"reply": f"Here is what I found for '{clean_msg.title()}':", "movies": local_results}

        # 4. Fallback: If it's a long descriptive query, use semantic search
        if len(clean_msg.split()) >= 3 or len(clean_msg) > 15:
            semantic_results = search_vibe(clean_msg, n=15)
            if semantic_results and not isinstance(semantic_results, dict) and len(semantic_results) > 0:
                return {"reply": "Here are some titles that match that vibe:", "movies": semantic_results}

        # 5. Last resort: Search TMDB Multi-Search directly
        search_url = f"{TMDB_BASE}/search/multi?api_key={TMDB_API_KEY}&query={clean_msg}&language=en-US"
        search_data = requests.get(search_url, timeout=10, verify=SSL_VERIFY).json()
        
        results = []
        for r in search_data.get("results", [])[:15]:
            if r.get("media_type") in ("movie", "tv"):
                poster = f"{POSTER_BASE}{r['poster_path']}" if r.get("poster_path") else PLACEHOLDER
                results.append({
                    "id": r["id"],
                    "title": r.get("title", r.get("name", "Unknown")),
                    "poster": poster,
                    "rating": r.get("vote_average", 0),
                    "media_type": r.get("media_type", "movie"),
                })
                
        if results:
            return {"reply": f"Here is what I found for '{clean_msg.title()}':", "movies": results}
            
        return {"reply": f"Sorry, I couldn't find anything matching '{clean_msg.title()}'."}
        
    except Exception as e:
        return {"reply": "Sorry, I ran into an issue finding those movies."}

@app.get("/api/trending")
def trending():
    try:
        results = []
        seen_ids = set()
        # Fetch 3 pages of trending (60 items) for a richer See All page
        for page in range(1, 4):
            url = f"{TMDB_BASE}/trending/all/week?api_key={TMDB_API_KEY}&language=en-US&page={page}"
            data = requests.get(url, timeout=5, verify=SSL_VERIFY).json()
            for r in data.get("results", []):
                if r["id"] in seen_ids:
                    continue
                seen_ids.add(r["id"])
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
                    "genres": ", ".join([str(g) for g in r.get("genre_ids", [])]),
                })
        return results
    except Exception as e:
        # Fallback to local most popular movies if TMDB Live Trending is rate limited or blocked
        subset = movies.head(40)
        results = []
        for _, row in subset.iterrows():
            results.append(row_to_dict(row))
        return results


@app.get("/api/vibes")
def get_vibes():
    return CLUSTERS

@app.get("/api/vibes/{cluster_id}")
def get_vibe_movies(cluster_id: int, n: int = 20):
    if "cluster_id" not in movies.columns:
        return []
    
    match = movies[movies["cluster_id"] == cluster_id]
    
    # Sort by rating or just take head for simplicity
    if "vote_average" in match.columns:
        match = match.sort_values(by="vote_average", ascending=False)
        
    subset = match.head(n)
    results = []
    for _, row in subset.iterrows():
        results.append(row_to_dict(row))
    return results


_encoder_model = None
def get_encoder():
    global _encoder_model
    if _encoder_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _encoder_model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            pass
    return _encoder_model

@app.get("/api/search/vibe")
def search_vibe(q: str, n: int = 15, diversity: float = 0.5):
    if index is None or movies.empty:
        return []
    
    encoder = get_encoder()
    if not encoder:
        return {"error": "Semantic search model not available. Install sentence-transformers."}
        
    query_vector = encoder.encode([q])
    faiss.normalize_L2(query_vector)
    
    # 1. Over-retrieve candidates
    fetch_n = min(n * 3 + 1, index.ntotal)
    distances, indices = index.search(query_vector, fetch_n)
    
    candidates = []
    for dist, idx in zip(distances[0], indices[0]):
        candidates.append((dist, idx))
        
    if not candidates:
        return []
        
    # 2. MMR Re-ranking
    selected_indices = []
    selected_vectors = []
    candidate_vectors = {idx: index.reconstruct(int(idx)) for _, idx in candidates}
    
    while len(selected_indices) < n and candidates:
        best_score = -float('inf')
        best_candidate_pos = -1
        
        for pos, (sim_to_query, idx) in enumerate(candidates):
            if not selected_vectors:
                mmr_score = sim_to_query
            else:
                v_c = candidate_vectors[idx]
                sims_to_selected = [np.dot(v_c, v_s) for v_s in selected_vectors]
                max_sim_to_selected = max(sims_to_selected)
                mmr_score = (1.0 - diversity) * sim_to_query - diversity * max_sim_to_selected
                
            if mmr_score > best_score:
                best_score = mmr_score
                best_candidate_pos = pos
                
        sim_to_query, best_idx = candidates.pop(best_candidate_pos)
        selected_indices.append((best_idx, sim_to_query))
        selected_vectors.append(candidate_vectors[best_idx])
        
    results = []
    
    stop_words = {"this", "that", "with", "from", "movie", "film", "series", "about", "their", "there", "which", "anime", "when", "into", "after"}
    query_words = set(w.lower() for w in q.split() if len(w) > 3 and w.lower() not in stop_words)
    
    for idx, sim in selected_indices:
        row = movies.iloc[idx]
        rec_dict = row_to_dict(row)
        rec_dict["similarity_score"] = float(sim)
        
        # Explain against query words
        rec_tags = set(w.lower() for w in row.get("tags", "").split() if len(w) > 3 and w.lower() not in stop_words)
        shared_themes = list(query_words.intersection(rec_tags))
        
        match_pct = min(100, max(0, int(sim * 100)))
        reason_parts = [f"{match_pct}% match"]
        
        if shared_themes:
            reason_parts.append(f"themes: {', '.join(shared_themes[:3])}")
            
        rec_dict["explanation"] = {
            "match_pct": match_pct,
            "shared_themes": shared_themes,
            "reason": " — ".join(reason_parts)
        }
        
        results.append(rec_dict)
        
    return results

class GroupRequest(BaseModel):
    users: list[list[int]]
    n: int = 10
    diversity: float = 0.5

@app.post("/api/group-recommend")
def group_recommend(req: GroupRequest):
    if index is None or movies.empty:
        return []
        
    if not req.users or all(not u for u in req.users):
        return []
        
    centroids = []
    user_valid_counts = []
    
    for user_movies in req.users:
        user_vectors = []
        for mid in user_movies:
            match = movies[movies["id"] == mid]
            if not match.empty:
                idx = match.index[0]
                user_vectors.append(index.reconstruct(int(idx)))
                
        if user_vectors:
            centroid = np.mean(user_vectors, axis=0)
            faiss.normalize_L2(np.array([centroid]))
            centroids.append(centroid)
            user_valid_counts.append(len(user_vectors))
        else:
            centroids.append(None)
            user_valid_counts.append(0)
            
    valid_centroids = [c for c in centroids if c is not None]
    if not valid_centroids:
        return []
        
    # Over-retrieve from all centroids
    fetch_n = min(req.n * 5 + 10, index.ntotal)
    candidate_indices = set()
    
    for centroid in valid_centroids:
        q_vec = np.array([centroid])
        _, indices = index.search(q_vec, fetch_n)
        for idx in indices[0]:
            candidate_indices.add(idx)
            
    # Filter out movies that were in the input sets
    input_ids = set()
    for u in req.users:
        input_ids.update(u)
        
    candidates = []
    candidate_vectors = {}
    for idx in candidate_indices:
        row = movies.iloc[idx]
        if row["id"] in input_ids:
            continue
            
        v_c = index.reconstruct(int(idx))
        candidate_vectors[idx] = v_c
        
        # Calculate fit for each user
        scores = []
        for centroid in valid_centroids:
            scores.append(np.dot(v_c, centroid))
            
        # Group score is the minimum score across users (ensures no one hates it)
        # plus a small weight for the average score
        min_score = min(scores)
        avg_score = sum(scores) / len(scores)
        group_score = min_score * 0.8 + avg_score * 0.2
        
        candidates.append((group_score, idx, scores))
        
    # Sort by group score
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    # MMR Re-ranking
    selected_indices = []
    selected_vectors = []
    
    while len(selected_indices) < req.n and candidates:
        best_score = -float('inf')
        best_candidate_pos = -1
        
        for pos, (sim_to_query, idx, user_scores) in enumerate(candidates):
            if not selected_vectors:
                mmr_score = sim_to_query
            else:
                v_c = candidate_vectors[idx]
                sims_to_selected = [np.dot(v_c, v_s) for v_s in selected_vectors]
                max_sim_to_selected = max(sims_to_selected)
                mmr_score = (1.0 - req.diversity) * sim_to_query - req.diversity * max_sim_to_selected
                
            if mmr_score > best_score:
                best_score = mmr_score
                best_candidate_pos = pos
                
        group_score, best_idx, user_scores = candidates.pop(best_candidate_pos)
        selected_indices.append((best_idx, group_score, user_scores))
        selected_vectors.append(candidate_vectors[best_idx])
        
    results = []
    for idx, group_sim, u_scores in selected_indices:
        row = movies.iloc[idx]
        rec_dict = row_to_dict(row)
        rec_dict["similarity_score"] = float(group_sim)
        
        rec_dict["user_scores"] = [min(100, max(0, int(s * 100))) for s in u_scores]
        match_pct = min(100, max(0, int(group_sim * 100)))
        
        rec_dict["explanation"] = {
            "match_pct": match_pct,
            "reason": f"{match_pct}% Group Consensus Match"
        }
        
        results.append(rec_dict)
        
    return results
