"""
Build a 10,000+ item dataset by fetching movies, TV shows, and anime
directly from the TMDB API. Then generate Sentence-BERT embeddings
and a FAISS index.

Usage: python build_dataset.py
"""
import requests
import urllib3
import ssl
import pandas as pd
import numpy as np
import pickle
import os
import time
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── Configuration from environment ─────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

API_KEY = os.getenv("TMDB_API_KEY")
if not API_KEY:
    print("ERROR: TMDB_API_KEY environment variable is not set.")
    print("Get one at https://www.themoviedb.org/settings/api")
    print("Then: set TMDB_API_KEY=your_key  (or add to .env file)")
    sys.exit(1)

DISABLE_SSL_VERIFY = os.getenv("DISABLE_SSL_VERIFY", "").lower() == "true"
SSL_VERIFY = not DISABLE_SSL_VERIFY

if DISABLE_SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://api.themoviedb.org/3"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Create a robust session with automatic retries
session = requests.Session()
retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
session.mount("https://", adapter)
session.mount("http://", adapter)

request_count = 0
request_window_start = time.time()

def api_get(url, max_attempts=4):
    global request_count, request_window_start
    request_count += 1
    if request_count >= 35:
        elapsed = time.time() - request_window_start
        if elapsed < 10:
            time.sleep(10 - elapsed + 1)
        request_count = 0
        request_window_start = time.time()

    for attempt in range(1, max_attempts + 1):
        try:
            r = session.get(url, timeout=20, verify=SSL_VERIFY)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < max_attempts:
                wait = attempt * 3
                print(f"    [RETRY {attempt}/{max_attempts}] Waiting {wait}s... ({type(e).__name__})")
                time.sleep(wait)
            else:
                print(f"    [WARN] Request failed after {max_attempts} attempts: {e}")
                return {}

print("=" * 60)
print("  CinemaTime Dataset Builder")
print("  Target: 10,000+ Movies, TV Shows, Anime")
print("=" * 60)

# ── Step 1: Load existing local CSV data if available ──────────
print("\n[1/6] Checking for existing local data...")
existing_df = None
csv_candidates = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmdb_5000_movies.csv"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "movies.csv"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "movies.csv"),
]
for csv_path in csv_candidates:
    if os.path.exists(csv_path):
        print(f"    Found local CSV: {csv_path}")
        try:
            raw = pd.read_csv(csv_path)
            # Normalize column names
            if "original_title" in raw.columns and "title" not in raw.columns:
                raw.rename(columns={"original_title": "title"}, inplace=True)
            if "title" in raw.columns and "overview" in raw.columns:
                existing_df = raw
                print(f"    Loaded {len(existing_df)} items from local CSV")
            break
        except Exception as e:
            print(f"    [WARN] Could not read CSV: {e}")

# Also check for existing pkl
pkl_path = os.path.join(OUTPUT_DIR, "movies.pkl")
if existing_df is None and os.path.exists(pkl_path):
    try:
        existing_df = pickle.load(open(pkl_path, "rb"))
        if len(existing_df) > 100:
            print(f"    Found existing pkl with {len(existing_df)} items")
        else:
            existing_df = None
    except Exception:
        existing_df = None

# ── Step 2: TMDB Fetcher (Movies + TV) ────────────────────────────
print("\n[2/6] Fetching movies & TV from TMDB...")
movie_genres_data = api_get(f"{BASE}/genre/movie/list?api_key={API_KEY}&language=en-US")
movie_genre_map = {g["id"]: g["name"] for g in movie_genres_data.get("genres", [])}
tv_genres_data = api_get(f"{BASE}/genre/tv/list?api_key={API_KEY}&language=en-US")
tv_genre_map = {g["id"]: g["name"] for g in tv_genres_data.get("genres", [])}

def fetch_tmdb_discover(endpoint, pages, genre_map, media_type, sort_by="popularity.desc", vote_count=20):
    """Generic TMDB discover fetcher."""
    items = []
    seen_ids = set()
    consecutive_failures = 0
    for page in range(1, pages + 1):
        url = f"{BASE}/discover/{endpoint}?api_key={API_KEY}&language=en-US&sort_by={sort_by}&page={page}&vote_count.gte={vote_count}"
        data = api_get(url)
        results = data.get("results", [])
        if not results:
            consecutive_failures += 1
            if consecutive_failures >= 3: break
            continue
        consecutive_failures = 0
        for r in results:
            rid = r["id"]
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            genres = [genre_map.get(gid, "") for gid in r.get("genre_ids", [])]
            title = r.get("title", r.get("name", "Unknown"))
            items.append({
                "id": f"tmdb_{rid}",
                "title": title,
                "overview": r.get("overview", ""),
                "genres": [g for g in genres if g],
                "vote_average": r.get("vote_average", 0),
                "poster_path": r.get("poster_path", "") or "",
                "backdrop_path": r.get("backdrop_path", "") or "",
                "release_date": r.get("release_date", r.get("first_air_date", "")),
                "media_type": media_type,
            })
        if page % 25 == 0:
            print(f"      {endpoint} [{sort_by[:12]}] Page {page}/{pages} - {len(items)} items")
    return items

# Fetch movies using multiple strategies to maximize unique content
# TMDB caps discover at 500 pages, but popular movies thin out after ~300
movie_items = []
seen_movie_ids = set()

strategies = [
    ("popularity.desc", 300, 20),                          # Most popular
    ("vote_average.desc", 100, 500),                       # Top rated (override base threshold)
    ("revenue.desc", 100, 20),                             # Highest grossing
    ("primary_release_date.desc", 100, 20),                # Newest
]

for sort_by, pages, vote_count in strategies:
    print(f"    Strategy: {sort_by} ({pages} pages)...")
    batch = fetch_tmdb_discover("movie", pages, movie_genre_map, "movie", sort_by, vote_count)
    for item in batch:
        if item["id"] not in seen_movie_ids:
            seen_movie_ids.add(item["id"])
            movie_items.append(item)

print(f"    ✅ Collected {len(movie_items)} unique movies from TMDB")

# Also fetch TV shows from TMDB (better metadata than TVmaze for popular shows)
print("    Fetching TV shows from TMDB...")
tmdb_tv_items = fetch_tmdb_discover("tv", 150, tv_genre_map, "tv", "popularity.desc")
print(f"    ✅ Collected {len(tmdb_tv_items)} TV shows from TMDB")

# ── Step 3: TVmaze Fetcher (TV Shows) ────────────────────────────
print("\n[3/6] Fetching TV Shows from TVmaze...")
import re
def fetch_tvmaze_shows(pages):
    items = []
    for page in range(pages):
        url = f"https://api.tvmaze.com/shows?page={page}"
        data = api_get(url)
        if not data or not isinstance(data, list): break
        for r in data:
            summary = r.get("summary", "") or ""
            clean_summary = re.sub(r'<[^>]+>', '', summary)
            items.append({
                "id": f"tvmaze_{r['id']}",
                "title": r.get("name", "Unknown"),
                "overview": clean_summary,
                "genres": r.get("genres", []),
                "vote_average": (r.get("rating") or {}).get("average", 0) or 0,
                "poster_path": (r.get("image") or {}).get("original", ""),
                "backdrop_path": (r.get("image") or {}).get("original", ""),
                "release_date": r.get("premiered", "") or "",
                "media_type": "tv",
            })
        if page % 5 == 0:
            print(f"      TVmaze Page {page}/{pages} - {len(items)} shows collected")
    return items

tv_items = fetch_tvmaze_shows(40) # 40 pages * 250 = ~10k shows
print(f"    Collected {len(tv_items)} TV shows from TVmaze")

# ── Step 4: Jikan Fetcher (Anime) ────────────────────────────────
print("\n[4/6] Fetching Anime from Jikan...")
def fetch_jikan_anime(pages):
    items = []
    for page in range(1, pages + 1):
        url = f"https://api.jikan.moe/v4/top/anime?page={page}"
        data = api_get(url)
        time.sleep(1) # Strict rate limit for Jikan
        
        results = data.get("data", []) if isinstance(data, dict) else []
        if not results: break
        
        for r in results:
            genres = [g["name"] for g in r.get("genres", [])]
            themes = [g["name"] for g in r.get("themes", [])]
            poster = r.get("images", {}).get("jpg", {}).get("large_image_url", "")
            date_str = r.get("aired", {}).get("from", "")
            if date_str: date_str = date_str.split("T")[0]
            
            items.append({
                "id": f"jikan_{r['mal_id']}",
                "title": r.get("title_english") or r.get("title", "Unknown"),
                "overview": r.get("synopsis", ""),
                "genres": genres + themes + ["Anime"],
                "vote_average": r.get("score", 0) or 0,
                "poster_path": poster,
                "backdrop_path": poster,
                "release_date": date_str,
                "media_type": "anime",
            })
        if page % 5 == 0:
            print(f"      Jikan Page {page}/{pages} - {len(items)} anime collected")
    return items

# Ask the user if they want to fetch Anime or skip it due to time
# Since it takes time, we'll fetch just 20 pages (500 anime) by default.
anime_items = fetch_jikan_anime(20) 
print(f"    Collected {len(anime_items)} Anime from Jikan")

# ── Step 5: Merge everything ──────────────────────────────────
print("\n[5/6] Merging all data sources...")
all_items = movie_items + tmdb_tv_items + tv_items + anime_items
api_df = pd.DataFrame(all_items) if all_items else pd.DataFrame()

if existing_df is not None and len(existing_df) > 0:
    print(f"    Merging {len(api_df)} API items with {len(existing_df)} local items...")
    
    # Convert old integer IDs to tmdb strings for backward compatibility
    existing_df["id"] = existing_df["id"].apply(lambda x: f"tmdb_{x}" if str(x).isdigit() else str(x))

    if "media_type" not in existing_df.columns:
        existing_df["media_type"] = "movie"
    if "genres_display" not in existing_df.columns:
        existing_df["genres_display"] = existing_df.get("genres", "").apply(lambda x: x if isinstance(x, str) else ", ".join(x) if isinstance(x, list) else "")
    if "cast_display" not in existing_df.columns:
        existing_df["cast_display"] = ""
    for col in ["vote_average", "poster_path", "backdrop_path", "release_date", "overview"]:
        if col not in existing_df.columns:
            existing_df[col] = 0 if col == "vote_average" else ""
            
    existing_df["tags"] = (
        existing_df["title"].astype(str).str.lower() + " "
        + existing_df["overview"].astype(str).str.lower() + " "
        + existing_df["genres_display"].astype(str).str.lower().str.replace(", ", " ") + " "
        + existing_df["media_type"].astype(str)
    )

    keep_cols = ["id", "title", "tags", "overview", "cast_display", "genres_display",
                 "vote_average", "poster_path", "backdrop_path", "release_date", "media_type"]
    for col in keep_cols:
        if col not in existing_df.columns:
            existing_df[col] = ""
    local_clean = existing_df[keep_cols].copy()
else:
    local_clean = pd.DataFrame()

if len(api_df) > 0:
    api_df["genres_display"] = api_df["genres"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    api_df["cast_display"] = ""
    api_df["tags"] = (
        api_df["title"].astype(str).str.lower() + " "
        + api_df["overview"].astype(str).str.lower() + " "
        + api_df["genres"].apply(lambda x: " ".join([g.lower().replace(" ", "") for g in x]) if isinstance(x, list) else "") + " "
        + api_df["media_type"].astype(str)
    )
    keep_cols = ["id", "title", "tags", "overview", "cast_display", "genres_display",
                 "vote_average", "poster_path", "backdrop_path", "release_date", "media_type"]
    api_clean = api_df[keep_cols].copy()
else:
    api_clean = pd.DataFrame()

# Combine: API data takes priority, then local
if len(api_clean) > 0 and len(local_clean) > 0:
    df = pd.concat([api_clean, local_clean], ignore_index=True)
elif len(api_clean) > 0:
    df = api_clean
elif len(local_clean) > 0:
    df = local_clean
else:
    print("\n" + "!" * 60)
    print("  CRITICAL ERROR: No data available from any source.")
    print("!" * 60)
    sys.exit(1)

# Deduplicate and clean — IDs are prefixed strings like "tmdb_550"
df["id"] = df["id"].astype(str)
df.drop_duplicates(subset=["id"], keep="first", inplace=True)
df = df[df["overview"].astype(str).str.len() > 10].copy()
df.reset_index(drop=True, inplace=True)

print(f"    Final dataset: {len(df)} items")
print(f"      Movies:  {len(df[df['media_type'] == 'movie'])}")
print(f"      TV:      {len(df[df['media_type'] == 'tv'])}")
print(f"      Anime:   {len(df[df['media_type'] == 'anime'])}")

# ── Step 6: Generate embeddings ───────────────────────────────
print("\n[6/6] Generating Sentence-BERT embeddings & FAISS index...")
from sentence_transformers import SentenceTransformer
import faiss

model = SentenceTransformer("all-MiniLM-L6-v2")
print("    Model loaded. Encoding...")
embeddings = model.encode(df["tags"].tolist(), show_progress_bar=True, batch_size=64)
print(f"    Embeddings shape: {embeddings.shape}")

dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
faiss.normalize_L2(embeddings)
index.add(embeddings)
print(f"    FAISS index built: {index.ntotal} vectors")

save_df = df[["id", "title", "tags", "overview", "cast_display", "genres_display",
              "vote_average", "poster_path", "backdrop_path", "release_date", "media_type"]].copy()

# ── Step 7: Vibe Clustering ────────────────────────────────────
print("\n[7/7] Generating Vibe Clusters...")
try:
    from sklearn.cluster import KMeans
    from collections import Counter
    import json

    n_clusters = 20
    # use fewer init/iters for speed in build
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=5, max_iter=100)
    labels = kmeans.fit_predict(embeddings)
    save_df["cluster_id"] = labels

    clusters = []
    stop_words = {"this", "that", "with", "from", "movie", "film", "series", "about", "their", "there", "which", "anime", "when", "into", "after"}
    emoji_map = ["🚀", "👻", "🤣", "💔", "🧙", "🔫", "🕵️", "🎸", "🥊", "👽", "🦄", "🌋", "🏰", "🤖", "🎨", "🎭", "🎪", "🏝️", "⛩️", "🛸"]

    for i in range(n_clusters):
        cluster_df = save_df[save_df["cluster_id"] == i]
        
        all_genres = []
        for g_list in cluster_df["genres_display"]:
            if pd.isna(g_list): continue
            for g in g_list.split(","):
                if g.strip(): all_genres.append(g.strip())
        top_genres = [g for g, _ in Counter(all_genres).most_common(3)]
        
        all_tags = []
        for tags in cluster_df["tags"]:
            if pd.isna(tags): continue
            for w in tags.split():
                if len(w) > 4 and w not in stop_words:
                    all_tags.append(w)
        top_tags = [t for t, _ in Counter(all_tags).most_common(5)]
        
        name = " & ".join(top_genres[:2]) if len(top_genres) >= 2 else (top_genres[0] if top_genres else "Mixed")
        if top_tags:
            name += f" ({top_tags[0].title()})"
            
        emoji = emoji_map[i % len(emoji_map)]
        
        # fix sample poster paths to absolute urls for frontend
        samples = cluster_df[cluster_df["poster_path"] != ""].head(3).to_dict('records')
        sample_list = []
        for s in samples:
            pp = s.get("poster_path", "")
            poster_url = pp if pp.startswith("http") else f"https://image.tmdb.org/t/p/w500{pp}" if pp else ""
            sample_list.append({
                "id": s["id"], 
                "title": s["title"], 
                "poster": poster_url,
                "media_type": s["media_type"]
            })
            
        clusters.append({
            "id": i,
            "name": f"{emoji} {name}",
            "description": f"Vibes: {', '.join(top_tags)}",
            "top_genres": top_genres,
            "size": len(cluster_df),
            "samples": sample_list
        })

    clusters_out = os.path.join(OUTPUT_DIR, "clusters.json")
    with open(clusters_out, "w") as f:
        json.dump(clusters, f, indent=2)
    print(f"    Saved {n_clusters} clusters to {clusters_out}")
except Exception as e:
    print(f"    [WARN] Clustering failed (scikit-learn missing?): {e}")
    save_df["cluster_id"] = -1

pkl_out = os.path.join(OUTPUT_DIR, "movies.pkl")
idx_out = os.path.join(OUTPUT_DIR, "movies.index")
pickle.dump(save_df, open(pkl_out, "wb"))
faiss.write_index(index, idx_out)

print(f"\n{'=' * 60}")
print(f"  SUCCESS! {len(save_df)} items saved:")
print(f"    {pkl_out}")
print(f"    {idx_out}")
print(f"{'=' * 60}")
print(f"\nRestart backend:  cd backend && uvicorn main:app --reload --port 8000")
