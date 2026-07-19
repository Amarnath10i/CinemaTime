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

# ── Step 2: Fetch genre maps ──────────────────────────────────
print("\n[2/6] Fetching genre maps...")
movie_genres_data = api_get(f"{BASE}/genre/movie/list?api_key={API_KEY}&language=en-US")
tv_genres_data = api_get(f"{BASE}/genre/tv/list?api_key={API_KEY}&language=en-US")
movie_genre_map = {g["id"]: g["name"] for g in movie_genres_data.get("genres", [])}
tv_genre_map = {g["id"]: g["name"] for g in tv_genres_data.get("genres", [])}
print(f"    Movie genres: {len(movie_genre_map)}, TV genres: {len(tv_genre_map)}")

def fetch_discover(media_type, pages, genre_map, extra_params=""):
    items = []
    title_key = "title" if media_type == "movie" else "name"
    date_key = "release_date" if media_type == "movie" else "first_air_date"
    consecutive_failures = 0
    for page in range(1, pages + 1):
        url = (
            f"{BASE}/discover/{media_type}?api_key={API_KEY}"
            f"&language=en-US&sort_by=popularity.desc&page={page}"
            f"&vote_count.gte=50{extra_params}"
        )
        data = api_get(url)
        results = data.get("results", [])
        if not results:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print(f"      Stopping after {consecutive_failures} consecutive empty pages")
                break
            continue
        consecutive_failures = 0
        for r in results:
            genres = [genre_map.get(gid, "") for gid in r.get("genre_ids", [])]
            genres = [g for g in genres if g]
            items.append({
                "id": r["id"],
                "title": r.get(title_key, "Unknown"),
                "overview": r.get("overview", ""),
                "genres": genres,
                "vote_average": r.get("vote_average", 0),
                "poster_path": r.get("poster_path", ""),
                "backdrop_path": r.get("backdrop_path", ""),
                "release_date": r.get(date_key, ""),
                "media_type": media_type,
            })
        if page % 10 == 0:
            print(f"      Page {page}/{pages} - {len(items)} items collected")
    return items

# ── Step 3: Fetch from TMDB API ───────────────────────────────
print("\n[3/6] Fetching movies from TMDB...")
movie_items = fetch_discover("movie", 250, movie_genre_map)
print(f"    Collected {len(movie_items)} movies from TMDB")

print("\n[4/6] Fetching TV shows & anime from TMDB...")
tv_items = fetch_discover("tv", 150, tv_genre_map)
anime_items = fetch_discover("tv", 100, tv_genre_map, "&with_genres=16&with_original_language=ja")
for item in anime_items:
    if "Anime" not in item["genres"]:
        item["genres"].append("Anime")
    item["media_type"] = "anime"
print(f"    TV Shows: {len(tv_items)}, Anime: {len(anime_items)}")

# ── Step 5: Merge everything ──────────────────────────────────
print("\n[5/6] Merging all data sources...")
all_items = movie_items + tv_items + anime_items
api_df = pd.DataFrame(all_items) if all_items else pd.DataFrame()

# Merge with existing local data
if existing_df is not None and len(existing_df) > 0:
    print(f"    Merging {len(api_df)} API items with {len(existing_df)} local items...")

    # Normalize existing_df to have the same columns
    if "media_type" not in existing_df.columns:
        existing_df["media_type"] = "movie"
    if "genres_display" not in existing_df.columns:
        # Try to extract genres from various possible column formats
        if "genres" in existing_df.columns:
            existing_df["genres_display"] = existing_df["genres"].apply(
                lambda x: x if isinstance(x, str) else ", ".join(x) if isinstance(x, list) else ""
            )
        else:
            existing_df["genres_display"] = ""
    if "cast_display" not in existing_df.columns:
        if "cast" in existing_df.columns:
            existing_df["cast_display"] = existing_df["cast"].apply(
                lambda x: x if isinstance(x, str) else ""
            )
        else:
            existing_df["cast_display"] = ""
    if "vote_average" not in existing_df.columns:
        existing_df["vote_average"] = 0
    if "poster_path" not in existing_df.columns:
        existing_df["poster_path"] = ""
    if "backdrop_path" not in existing_df.columns:
        existing_df["backdrop_path"] = ""
    if "release_date" not in existing_df.columns:
        existing_df["release_date"] = ""
    if "overview" not in existing_df.columns:
        existing_df["overview"] = ""

    # Build tags for existing data
    existing_df["tags"] = (
        existing_df["title"].astype(str).str.lower() + " "
        + existing_df["overview"].astype(str).str.lower() + " "
        + existing_df["genres_display"].astype(str).str.lower().str.replace(", ", " ") + " "
        + existing_df["media_type"].astype(str)
    )

    # Select common columns
    keep_cols = ["id", "title", "tags", "overview", "cast_display", "genres_display",
                 "vote_average", "poster_path", "backdrop_path", "release_date", "media_type"]
    for col in keep_cols:
        if col not in existing_df.columns:
            existing_df[col] = ""

    local_clean = existing_df[keep_cols].copy()
else:
    local_clean = pd.DataFrame()

# Process API data
if len(api_df) > 0:
    api_df["genres_display"] = api_df["genres"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    api_df["cast_display"] = ""
    api_df["tags"] = (
        api_df["title"].str.lower() + " "
        + api_df["overview"].str.lower() + " "
        + api_df["genres"].apply(lambda x: " ".join([g.lower().replace(" ", "") for g in x]) if isinstance(x, list) else "") + " "
        + api_df["media_type"]
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

# Deduplicate and clean
df["id"] = pd.to_numeric(df["id"], errors="coerce")
df.dropna(subset=["id"], inplace=True)
df["id"] = df["id"].astype(int)
df.drop_duplicates(subset=["id", "media_type"], keep="first", inplace=True)
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
            sample_list.append({
                "id": s["id"], 
                "title": s["title"], 
                "poster": f"https://image.tmdb.org/t/p/w500{s['poster_path']}" if s['poster_path'] else "", 
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
