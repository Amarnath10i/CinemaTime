# 🎬 CineMatch – AI Movie Recommendation System

A state-of-the-art movie recommendation engine powered by **Sentence-BERT** (`all-mpnet-base-v2`), **FAISS** vector search, the **MovieLens 25M** dataset, and **TMDB** metadata — served through a **FastAPI** backend and a premium **Next.js** frontend.

---

## ✨ Features

- **Semantic Search**: Uses Sentence-BERT to understand movie descriptions, genres, cast, and directors contextually — not just keyword matching.
- **FAISS Vector Index**: Lightning-fast similarity search across 62,000+ movies using Facebook AI Similarity Search.
- **Rich Movie Details**: Poster, backdrop, synopsis, rating, runtime, genres, and release date from TMDB.
- **Trailers**: Embedded YouTube trailers fetched directly from TMDB.
- **Cast Exploration**: Click on any actor to see their full filmography and biography.
- **Premium UI**: Cinematic dark theme with glassmorphism, Framer Motion animations, and responsive Tailwind CSS.

---

## 🏗 Architecture

```
movie-recommender-system/
├── model.ipynb          # Data pipeline: merge datasets → SBERT embeddings → FAISS index
├── backend/
│   ├── main.py          # FastAPI server (REST API)
│   ├── movies.pkl       # (generated) Movie metadata DataFrame
│   ├── movies.index     # (generated) FAISS vector index
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.js          # Root layout
│   │   ├── globals.css        # Tailwind + custom styles
│   │   ├── page.js            # Home: search + recommendations
│   │   ├── movie/[id]/page.js # Movie detail: trailer, cast, similar
│   │   └── cast/[id]/page.js  # Actor bio + filmography
│   ├── package.json
│   ├── next.config.js
│   └── tailwind.config.js
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+
- MovieLens 25M dataset (`movies.csv`, `links.csv`)
- TMDB 5000 dataset (`tmdb_5000_movies.csv`, `tmdb_5000_credits.csv`)

### 1. Generate Embeddings
```bash
pip install sentence-transformers faiss-cpu pandas numpy requests
```
Open `model.ipynb` and update the file paths to point to your local CSV files. Then **Run All Cells**. This will generate `backend/movies.pkl` and `backend/movies.index`.

### 2. Start the Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🛠 Tech Stack

| Layer       | Technology                              |
|-------------|-----------------------------------------|
| Embeddings  | Sentence-BERT (`all-mpnet-base-v2`)     |
| Search      | FAISS (`IndexFlatIP`)                   |
| Dataset     | MovieLens 25M + TMDB 5000              |
| Backend     | FastAPI + Python                        |
| Frontend    | Next.js 14 + Tailwind CSS + Framer Motion |
| Metadata    | TMDB API (posters, trailers, cast)      |

---

## 📄 License
MIT
