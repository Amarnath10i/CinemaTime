"""
Test the trained recommendation model.
Covers Movies, TV Shows/Web Series, and Anime.
"""
import pickle
import numpy as np
import faiss
import os

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")

print("=" * 60)
print("  CineMatch Model Test Suite")
print("  Movies · TV Shows · Anime")
print("=" * 60)

# Load
print("\n[1] Loading model artifacts...")
movies = pickle.load(open(os.path.join(BASE_DIR, "movies.pkl"), "rb"))
index = faiss.read_index(os.path.join(BASE_DIR, "movies.index"))
print(f"    Dataset: {len(movies)} items")
print(f"    FAISS index: {index.ntotal} vectors, {index.d} dimensions")
print(f"    Columns: {list(movies.columns)}")

if "media_type" in movies.columns:
    for mt in movies["media_type"].unique():
        print(f"    [{mt}]: {len(movies[movies['media_type'] == mt])}")
else:
    print("    [all movies — no media_type column yet]")
    print("    Run build_dataset.py to get TV shows & anime!")

# Recommend function
def recommend(title, n=5):
    match = movies[movies["title"].str.contains(title, case=False, na=False)]
    if match.empty:
        print(f"\n  ❌ '{title}' not found in dataset. (Will be available after build_dataset.py)")
        return
    row = match.iloc[0]
    movie_idx = match.index[0]
    mt = row.get("media_type", "movie") if "media_type" in movies.columns else "movie"
    genres = row.get("genres_display", "") if "genres_display" in movies.columns else ""
    print(f"\n  🎯 Query: {row['title']}  [{mt}]")
    print(f"     Genres: {genres}")
    print(f"     Rating: ⭐ {row['vote_average']}")
    print(f"     {'─' * 48}")

    query_vector = index.reconstruct(int(movie_idx))
    query_vector = np.array([query_vector])
    distances, indices = index.search(query_vector, n + 1)

    rank = 1
    for i, dist in zip(indices[0], distances[0]):
        if i == movie_idx:
            continue
        r = movies.iloc[i]
        r_mt = r.get("media_type", "movie") if "media_type" in movies.columns else "movie"
        r_genres = r.get("genres_display", "") if "genres_display" in movies.columns else ""
        emoji = {"movie": "🎬", "tv": "📺", "anime": "🌸"}.get(r_mt, "🎬")
        print(f"     {rank}. {emoji} {r['title']}  (similarity: {dist:.4f})  ⭐{r['vote_average']}  [{r_mt}]")
        print(f"        {r_genres}")
        rank += 1
        if rank > n:
            break


# ── MOVIE TESTS ────────────────────────────────────────────
print("\n" + "═" * 60)
print("  🎬 MOVIE RECOMMENDATIONS")
print("═" * 60)

recommend("The Dark Knight")
recommend("Interstellar")
recommend("Titanic")
recommend("Toy Story")
recommend("The Conjuring")
recommend("The Avengers")

# ── TV / WEB SERIES TESTS ─────────────────────────────────
print("\n" + "═" * 60)
print("  📺 TV SHOW / WEB SERIES RECOMMENDATIONS")
print("═" * 60)

recommend("Breaking Bad")
recommend("Stranger Things")
recommend("Game of Thrones")
recommend("The Witcher")
recommend("Money Heist")

# ── ANIME TESTS ───────────────────────────────────────────
print("\n" + "═" * 60)
print("  🌸 ANIME RECOMMENDATIONS")
print("═" * 60)

recommend("Attack on Titan")
recommend("Death Note")
recommend("Naruto")
recommend("One Piece")
recommend("Demon Slayer")
recommend("Dragon Ball")

# ── SUMMARY ───────────────────────────────────────────────
print("\n" + "═" * 60)
print("  ✅ ALL TESTS COMPLETE")
print("═" * 60)

found = 0
not_found = 0
test_titles = [
    "The Dark Knight", "Interstellar", "Titanic", "Toy Story", "The Conjuring", "The Avengers",
    "Breaking Bad", "Stranger Things", "Game of Thrones", "The Witcher", "Money Heist",
    "Attack on Titan", "Death Note", "Naruto", "One Piece", "Demon Slayer", "Dragon Ball"
]
for t in test_titles:
    if movies["title"].str.contains(t, case=False, na=False).any():
        found += 1
    else:
        not_found += 1

print(f"\n  Dataset Coverage: {found}/{len(test_titles)} test titles found")
if not_found > 0:
    print(f"  ⚠ {not_found} titles missing — run 'python build_dataset.py' to expand dataset with TV & Anime!")
else:
    print(f"  🎉 Perfect coverage! All movies, TV shows, and anime are in the dataset.")
