# 🍿 CinemaTime (formerly CineMatch)

CinemaTime is an AI-powered movie, TV show, and anime recommendation engine. It uses a FAISS vector database and `SentenceTransformers` to understand the *semantic meaning* of media, moving beyond simple genre matching to true contextual recommendations.

## 🚀 Key Features

### 1. 🧠 Semantic Search (Natural Language Queries)
Instead of searching by exact title, you can ask CinemaTime descriptive queries like *"something like Interstellar but funnier"*. The backend lazy-loads the `all-MiniLM-L6-v2` SentenceTransformer model to encode your query into a vector and searches the FAISS index to find the closest thematic matches.

### 2. ⚖️ Diversity-Aware Re-ranking (MMR)
To prevent "the superhero problem" (where recommending one Marvel movie just returns 10 more Marvel movies), CinemaTime uses **Maximal Marginal Relevance (MMR)**. It balances relevance against diversity, ensuring you get a varied list of high-quality recommendations.

### 3. 🔍 Explainable Recommendations
Machine learning shouldn't be a black box. CinemaTime compares the metadata and thematic tags (TF-IDF keyword overlap) of the source and recommended items, returning a human-readable explanation (e.g., `82% match — similar themes: time travel, space`) displayed on the frontend.

### 4. 🤝 Group Watch Consensus Mode
Can't decide what to watch with friends? Group Watch allows up to 5 people to input their favorite movies. The AI computes a taste centroid for each user, then searches the vector space for movies that minimize the distance to *all* centroids simultaneously. A visual compatibility bar shows how well the consensus pick matches each user.

### 5. 🔮 Vibe Clusters (Mood Browsing)
The offline `build_dataset.py` pipeline runs k-Means clustering over the semantic embeddings, automatically categorizing thousands of movies and shows into browsable "Vibe" clusters (e.g., "Dark Thrillers", "Cozy Romances").

### 6. 🎬 Trailers for Everything
Every movie, TV show and anime gets a trailer, teaser, promo or clip. [`backend/trailers.py`](backend/trailers.py) tries, in order:
1. **TMDB videos**, in English and the title's original language; TV shows with none fall back to their seasons' videos.
2. **Jikan** trailers, PVs/teasers/CMs and opening/ending videos for MyAnimeList anime.
3. **TMDB cross-references**: TVmaze shows by IMDb/TheTVDB id, Jikan anime by title.
4. **YouTube search**, keeping only results that name the title. It uses the YouTube Data API when `YOUTUBE_API_KEY` is set, otherwise the public results page.

`GET /api/trailers/{id}?type=movie|tv|anime` returns just the videos and is cached in memory. In the browser, the player skips any video YouTube won't embed and moves on to the next.

## 🛠️ Multi-API Architecture

CinemaTime aggregates data from three different sources into a unified FAISS index:
- **Movies**: TMDB (`tmdb_{id}`)
- **TV Shows**: TVmaze (`tvmaze_{id}`)
- **Anime**: Jikan / MyAnimeList (`jikan_{id}`)

## 💻 Tech Stack

* **Frontend**: Next.js 14, React, TailwindCSS, Framer Motion
* **Backend**: FastAPI (Python), Pandas
* **Machine Learning**: `faiss-cpu`, `scikit-learn`, `sentence-transformers`

## ⚙️ Running Locally

1. **Environment Setup**
   Create a `.env` file in the root (or `backend/`) directory:
   ```env
   TMDB_API_KEY=your_api_key_here
   # Optional: official YouTube search for the trailer fallback (see below)
   YOUTUBE_API_KEY=
   DISABLE_SSL_VERIFY=false
   ```

2. **Backend & Dataset**
   ```bash
   cd backend
   pip install -r requirements.txt
   
   # Build the FAISS index and Clusters (Takes time due to API rate limits!)
   python ../build_dataset.py
   
   # Run the API server
   uvicorn main:app --reload --port 8000
   ```

3. **Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## 🧪 Testing & Evaluation
The backend includes a Pytest suite, and a GitHub Action workflow automatically runs tests on push/PR to `main`.
```bash
cd backend
pytest tests/
```

We have also written an algorithmic evaluation for the group consensus model. To run it:
```bash
python backend/eval_group_rec.py
```

## 📄 Documentation
For an in-depth breakdown of the Machine Learning architecture, including the Social Choice theory behind Group Consensus, MMR math, and FAISS scale/latency considerations, please read the **[Technical Report](docs/TECHNICAL_REPORT.md)**.
