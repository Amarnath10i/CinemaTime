"""
Build a 10,000+ item dataset by fetching movies, TV shows, and anime
directly from the TMDB API. Then generate Sentence-BERT embeddings
and a FAISS index.

Usage: python build_dataset.py
"""
import requests
import pandas as pd
import numpy as np
import pickle
import os
import time
import sys

API_KEY = "10e0997eacd8c14e60ef40b8a46f695b"
BASE = "https://api.themoviedb.org/3"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
os.makedirs(OUTPUT_DIR, exist_ok=True)

request_count = 0
request_window_start = time.time()

def api_get(url):
    global request_count, request_window_start
    request_count += 1
    if request_count >= 38:
        elapsed = time.time() - request_window_start
        if elapsed < 10:
            time.sleep(10 - elapsed + 0.5)
        request_count = 0
        request_window_start = time.time()
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"    [WARN] Request failed: {e}")
        return {}

print("=" * 60)
print("  CineMatch Dataset Builder")
print("  Target: 10,000+ Movies, TV Shows, Anime")
print("=" * 60)

print("\n[1/5] Fetching genre maps...")
movie_genres_data = api_get(f"{BASE}/genre/movie/list?api_key={API_KEY}&language=en-US")
tv_genres_data = api_get(f"{BASE}/genre/tv/list?api_key={API_KEY}&language=en-US")
movie_genre_map = {g["id"]: g["name"] for g in movie_genres_data.get("genres", [])}
tv_genre_map = {g["id"]: g["name"] for g in tv_genres_data.get("genres", [])}
print(f"    Movie genres: {len(movie_genre_map)}, TV genres: {len(tv_genre_map)}")

def fetch_discover(media_type, pages, genre_map, extra_params=""):
    items = []
    title_key = "title" if media_type == "movie" else "name"
    date_key = "release_date" if media_type == "movie" else "first_air_date"
    for page in range(1, pages + 1):
        url = (
            f"{BASE}/discover/{media_type}?api_key={API_KEY}"
            f"&language=en-US&sort_by=popularity.desc&page={page}"
            f"&vote_count.gte=50{extra_params}"
        )
        data = api_get(url)
        results = data.get("results", [])
        if not results:
            break
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
        if page % 25 == 0:
            print(f"      Page {page}/{pages} - {len(items)} items collected")
    return items

print("\n[2/5] Fetching movies...")
movie_items = fetch_discover("movie", 250, movie_genre_map)
print(f"    Collected {len(movie_items)} movies")

print("\n[3/5] Fetching TV shows & anime...")
tv_items = fetch_discover("tv", 150, tv_genre_map)
anime_items = fetch_discover("tv", 100, tv_genre_map, "&with_genres=16&with_original_language=ja")
for item in anime_items:
    if "Anime" not in item["genres"]:
        item["genres"].append("Anime")
    item["media_type"] = "anime"
print(f"    TV Shows: {len(tv_items)}, Anime: {len(anime_items)}")

print("\n[4/5] Merging and deduplicating...")
all_items = movie_items + tv_items + anime_items

if not all_items:
    print("\n" + "!" * 60)
    print("  CRITICAL ERROR: No data was fetched from TMDB API.")
    print("  This is usually caused by an internet connection issue or a DNS problem.")
    print("  Please check if you can open https://api.themoviedb.org in your browser.")
    print("!" * 60)
    sys.exit(1)

df = pd.DataFrame(all_items)
df.drop_duplicates(subset=["id", "media_type"], keep="first", inplace=True)
df = df[df["overview"].str.len() > 10].copy()
df.reset_index(drop=True, inplace=True)
df["genres_display"] = df["genres"].apply(lambda x: ", ".join(x))
df["cast_display"] = ""
df["tags"] = (
    df["title"].str.lower() + " "
    + df["overview"].str.lower() + " "
    + df["genres"].apply(lambda x: " ".join([g.lower().replace(" ", "") for g in x])) + " "
    + df["media_type"]
)
print(f"    Final dataset: {len(df)} items")
print(f"      Movies:  {len(df[df['media_type'] == 'movie'])}")
print(f"      TV:      {len(df[df['media_type'] == 'tv'])}")
print(f"      Anime:   {len(df[df['media_type'] == 'anime'])}")

print("\n[5/5] Generating Sentence-BERT embeddings & FAISS index...")
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

pkl_path = os.path.join(OUTPUT_DIR, "movies.pkl")
idx_path = os.path.join(OUTPUT_DIR, "movies.index")
pickle.dump(save_df, open(pkl_path, "wb"))
faiss.write_index(index, idx_path)

print(f"\n{'=' * 60}")
print(f"  SUCCESS! {len(save_df)} items saved:")
print(f"    {pkl_path}")
print(f"    {idx_path}")
print(f"{'=' * 60}")
print(f"\nStart backend:  cd backend && uvicorn main:app --reload --port 8000")
