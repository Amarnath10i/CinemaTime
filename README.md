# CinemaTime

A movie, TV and anime discovery app whose **For You** page is a two-stage
recommender trained on **MovieLens 32M**: four retrievers (recency-weighted
EASE, implicit ALS with a content map for cold-start films, content and
popularity) re-ranked by LightGBM LambdaRank. It is evaluated on a later year
it never saw, ranks the full catalog, and is served by a NumPy-only engine that
is tested to reproduce the offline model exactly.

The full evaluation protocol, models and limitations are in
**[ml/README.md](ml/README.md)**; every number below links back to a report in
[`ml/reports/`](ml/reports/).

## Results

Models see likes (4+ stars) before 2022-10-12 and rank all 8,926 catalog
movies for 5,396 users, scored on the 87,958 movies those users liked in the
following year. 95% bootstrap intervals over users.

| model | NDCG@20 | Recall@20 | Hit@10 |
|---|---|---|---|
| Content: SBERT profile (what the app used before) | 0.0062 (0.0056–0.0070) | 0.0064 | 0.042 |
| Popularity, last 12 months | 0.0851 (0.0814–0.0887) | 0.0956 | 0.346 |
| Implicit ALS (k = 64) | 0.0805 (0.0770–0.0844) | 0.0792 | 0.325 |
| EASE, recency-weighted | 0.1240 (0.1194–0.1284) | 0.1257 | 0.465 |
| **Two-stage: 4 retrievers → LambdaRank** | **0.1405 (0.1364–0.1452)** | **0.1428** | **0.512** |
| *same model, served by the API's NumPy engine* | *0.1405 (0.1363–0.1451)* | *0.1427* | |

- **+13% over the best single model** (paired 95% interval +0.0129 to +0.0198 NDCG@20), and 23× the NDCG of the content model the app shipped before.
- **Serving is exact:** replaying every test user through the API engine changes NDCG@20 by −0.0000 (−0.0005 to +0.0004); a request takes ~17 ms at the median.
- **Cold start:** 8.8% of next-year likes went to movies with no ratings before the cutoff. Mapping SBERT vectors into the ALS space ranks them at NDCG@20 0.080, against 0.013 for content similarity.
- **Findings that changed the app:** a release-date mask (a quarter of the catalog postdates the ratings), training the ranker on the pruned EASE it is served with (the dense one cost 0.0025 NDCG), and evidence that Group Watch's least-misery rule serves members worse than "most pleasure".

## How it works

```
likes (browser) ──► retrievers ──────────────────────────────► candidates ──► LambdaRank ──► For You
                    EASE (recency-weighted, pruned CSR)            │          14 shared       + "Because you
                    implicit ALS, user folded in at request time   │          features          liked X"
                    hybrid ALS (SBERT → ALS map, cold start)       │
                    content (SBERT) + popularity                   ┘
```

- **Offline (`ml/`)**: catalog join to MovieLens via TMDB ids, temporal folds, full-catalog metrics with bootstrap and paired comparisons, EASE / item-kNN / ALS implemented from their papers and tested against their definitions, LightGBM LambdaRank, ablations, cold-start and short-history replays.
- **Serving (`backend/recsys/`)**: the exported arrays are scored with NumPy only; LightGBM trees are flattened and evaluated by a NumPy evaluator that is tested to match LightGBM, including missing-value routing. Ranker features are defined once and imported by both training and the API.
- **Explanations are exact:** an EASE score is a sum of per-liked-movie contributions, so "Because you liked X" names the largest one.

## The app

- **For You** (`/for-you`): heart a few movies (stored in the browser, no account) and get a ranked catalog with reasons; `/how-it-works` shows the model card and offline results.
- **Semantic search**: free-text queries ("something like Interstellar but funnier") encoded with `all-MiniLM-L6-v2` and searched in a FAISS index of movies, TV shows (TVmaze) and anime (Jikan).
- **Diversity re-ranking** with Maximal Marginal Relevance, and keyword-overlap explanations for similar-title recommendations.
- **Group Watch**: up to five people enter favourites; the app finds titles close to every member's taste centroid.
- **Vibe clusters**: k-means over the semantic embeddings for mood browsing.
- **Trailers** for every title, falling back from TMDB to Jikan, TMDB cross-references and YouTube search.

## Stack

- **Offline ML**: Python, NumPy/SciPy, LightGBM, `uv`
- **API**: FastAPI, FAISS, sentence-transformers
- **Frontend**: Next.js 14, React, Tailwind CSS

## Layout

```
ml/                 training and evaluation package (cinemaml), tests, reports
backend/            FastAPI app; recsys/ is the NumPy serving engine and shared features
frontend/           Next.js app
build_dataset.py    builds the FAISS index and vibe clusters from TMDB, TVmaze and Jikan
docs/               technical report (MMR, group consensus, FAISS latency)
```

## Run locally

```bash
# API (needs TMDB_API_KEY in backend/.env; YOUTUBE_API_KEY is optional)
cd backend
pip install -r requirements-ml.txt        # requirements.txt alone runs everything but free-text search
python ../build_dataset.py                # FAISS index and clusters; slow because of API rate limits
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

Reproducing the recommender (MovieLens 32M download, tuning, comparison, export) is described step by step in [ml/README.md](ml/README.md#reproduce).

## Tests

```bash
cd backend && pytest tests/
cd ml && uv run pytest     # models vs. their definitions, NumPy trees vs. LightGBM, engine vs. offline ranker
```

Both suites run in GitHub Actions on pushes and pull requests to `main`.

## Deploying

The frontend and API deploy as two Vercel projects from this repo (root directories `frontend` and `backend`). PyTorch does not fit Vercel's 500 MB function limit, so free-text search is unavailable there; For You, clusters, Group Watch and trailers work.
