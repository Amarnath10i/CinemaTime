"use client";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";

/* ── Movie Card ────────────────────────────── */
function MovieCard({ movie, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.4 }}
    >
      <Link href={`/movie/${movie.id}`}>
        <div className="group relative w-[180px] cursor-pointer">
          <div className="overflow-hidden rounded-xl">
            <img
              src={movie.poster}
              alt={movie.title}
              className="w-full h-[270px] object-cover transition-transform duration-500 group-hover:scale-110"
            />
            {/* Rating badge */}
            <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm text-yellow-400 text-xs font-bold px-2 py-1 rounded-md flex items-center gap-1">
              ⭐ {movie.rating?.toFixed(1) || "N/A"}
            </div>
          </div>
          <p className="mt-2 text-sm font-semibold text-gray-200 group-hover:text-accent transition-colors line-clamp-2">
            {movie.title}
          </p>
          {movie.release_date && (
            <p className="text-xs text-gray-500">{movie.release_date?.slice(0, 4)}</p>
          )}
        </div>
      </Link>
    </motion.div>
  );
}

/* ── Search Bar ────────────────────────────── */
function SearchBar({ onSelect }) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/movies/titles?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setSuggestions(data);
        setOpen(true);
      } catch (_) {
        setSuggestions([]);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div ref={ref} className="relative w-full max-w-2xl mx-auto">
      <div className="relative">
        <input
          id="search-bar"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search movies by title..."
          className="w-full px-6 py-4 rounded-2xl bg-dark-700 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-accent/50 focus:ring-2 focus:ring-accent/20 transition-all text-lg"
        />
        <span className="absolute right-5 top-1/2 -translate-y-1/2 text-gray-500 text-xl">🔍</span>
      </div>
      <AnimatePresence>
        {open && suggestions.length > 0 && (
          <motion.ul
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="absolute z-50 mt-2 w-full glass rounded-xl max-h-80 overflow-y-auto shadow-2xl"
          >
            {suggestions.map((s) => (
              <li
                key={s.id}
                onClick={() => {
                  onSelect(s);
                  setQuery(s.title);
                  setOpen(false);
                }}
                className="px-5 py-3 hover:bg-accent/10 cursor-pointer transition-colors border-b border-white/5 last:border-0"
              >
                <span className="text-white font-medium">{s.title}</span>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── Home Page ─────────────────────────────── */
export default function HomePage() {
  const [recommendations, setRecommendations] = useState([]);
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSelect(movie) {
    setSelectedMovie(movie);
    setLoading(true);
    try {
      const res = await fetch(`/api/recommend/${movie.id}?n=15`);
      const data = await res.json();
      setRecommendations(data);
    } catch (_) {
      setRecommendations([]);
    }
    setLoading(false);
  }

  return (
    <main className="min-h-screen">
      {/* ── Hero ──────────────────────────── */}
      <section className="relative flex flex-col items-center justify-center pt-24 pb-16 px-4">
        {/* Background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-accent/10 rounded-full blur-[120px] pointer-events-none" />

        <motion.h1
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-5xl md:text-7xl font-black text-center mb-3 tracking-tight"
        >
          <span className="bg-gradient-to-r from-accent to-accent-light bg-clip-text text-transparent">
            CineMatch
          </span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-gray-400 text-lg mb-10 text-center max-w-xl"
        >
          AI-powered movie recommendations using Sentence-BERT semantic search
        </motion.p>

        <SearchBar onSelect={handleSelect} />
      </section>

      {/* ── Recommendations ───────────────── */}
      {selectedMovie && (
        <section className="px-6 md:px-12 pb-20">
          <h2 className="text-2xl font-bold mb-6">
            Movies similar to{" "}
            <span className="text-accent">{selectedMovie.title}</span>
          </h2>

          {loading ? (
            <div className="scroll-row">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="w-[180px] h-[270px] rounded-xl shimmer flex-shrink-0" />
              ))}
            </div>
          ) : (
            <div className="scroll-row">
              {recommendations.map((m, i) => (
                <MovieCard key={m.id} movie={m} index={i} />
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Footer ────────────────────────── */}
      <footer className="text-center py-8 text-gray-600 text-sm border-t border-white/5">
        Built with Sentence-BERT · FAISS · MovieLens 25M · TMDB · Next.js
      </footer>
    </main>
  );
}
