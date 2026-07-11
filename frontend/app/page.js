"use client";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";

/* ── Media Badge ───────────────────────────── */
function MediaBadge({ type }) {
  const config = {
    movie: { emoji: "🎬", label: "Movie", bg: "bg-blue-500/20 text-blue-400" },
    tv: { emoji: "📺", label: "TV Series", bg: "bg-green-500/20 text-green-400" },
    anime: { emoji: "🌸", label: "Anime", bg: "bg-pink-500/20 text-pink-400" },
  };
  const c = config[type] || config.movie;
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${c.bg}`}>
      {c.emoji} {c.label}
    </span>
  );
}

/* ── Movie Card ────────────────────────────── */
function MovieCard({ movie, index: i }) {
  const [imageError, setImageError] = useState(false);
  const isPlaceholder = !movie.poster || movie.poster.includes("placeholder");
  const poster = isPlaceholder || imageError ? null : movie.poster;
  
  const hue1 = (movie.id * 137) % 360;
  const hue2 = (movie.id * 97) % 360;

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.04, duration: 0.4 }}
    >
      <Link href={`/movie/${movie.id}?type=${movie.media_type || "movie"}`}>
        <div className="group relative w-[180px] cursor-pointer">
          <div className="overflow-hidden rounded-xl h-[270px] bg-dark-800 relative border border-white/5 shadow-lg group-hover:border-accent/50 transition-colors">
            
            {poster ? (
              <img
                src={poster}
                alt={movie.title}
                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                onError={() => setImageError(true)}
              />
            ) : (
              <div 
                className="w-full h-full flex flex-col items-center justify-center p-4 text-center transition-transform duration-500 group-hover:scale-110"
                style={{
                  background: `linear-gradient(135deg, hsl(${hue1}, 70%, 20%), hsl(${hue2}, 60%, 10%))`
                }}
              >
                <div className="text-3xl mb-2 opacity-50">🎥</div>
                <h3 className="font-black text-white/90 text-lg leading-tight line-clamp-4 uppercase tracking-wider">{movie.title}</h3>
              </div>
            )}

            <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm text-yellow-400 text-xs font-bold px-2 py-1 rounded-md flex items-center gap-1 shadow-md border border-white/10">
              ⭐ {movie.rating?.toFixed(1) || "N/A"}
            </div>
            <div className="absolute top-2 left-2">
              <MediaBadge type={movie.media_type || "movie"} />
            </div>
            
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </div>

          <p className="mt-3 text-sm font-bold text-gray-200 group-hover:text-accent transition-colors line-clamp-2">
            {movie.title}
          </p>
          {movie.release_date && (
            <p className="text-xs text-gray-500 mt-1 font-medium">{movie.release_date?.slice(0, 4)}</p>
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
    if (query.length < 2) { setSuggestions([]); return; }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/movies/titles?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setSuggestions(data);
        setOpen(true);
      } catch (_) { setSuggestions([]); }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div ref={ref} className="relative w-full max-w-2xl mx-auto">
      <div className="relative group">
        <div className="absolute -inset-1 bg-gradient-to-r from-accent to-pink-600 rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
        <input
          id="search-bar"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for any movie, TV show, or anime..."
          className="relative w-full px-6 py-4 rounded-2xl bg-dark-800/90 backdrop-blur-xl border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/50 transition-all text-lg shadow-2xl"
        />
        <span className="absolute right-6 top-1/2 -translate-y-1/2 text-gray-400 text-xl group-hover:scale-110 transition-transform">🔍</span>
      </div>
      <AnimatePresence>
        {open && suggestions.length > 0 && (
          <motion.ul
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            className="absolute z-50 mt-3 w-full glass rounded-xl max-h-80 overflow-y-auto shadow-2xl border border-white/10 p-2"
          >
            {suggestions.map((s) => (
              <li
                key={`${s.id}-${s.media_type}`}
                onClick={() => { onSelect(s); setQuery(s.title); setOpen(false); }}
                className="px-4 py-3 hover:bg-white/5 rounded-lg cursor-pointer transition-all flex items-center justify-between group"
              >
                <span className="text-gray-300 group-hover:text-white font-medium transition-colors">{s.title}</span>
                <MediaBadge type={s.media_type || "movie"} />
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── Tab Filter ────────────────────────────── */
function Tabs({ active, onChange }) {
  const tabs = [
    { key: "all", label: "🔥 All Categories" },
    { key: "movie", label: "🎬 Movies" },
    { key: "tv", label: "📺 TV Series" },
    { key: "anime", label: "🌸 Anime" },
  ];
  return (
    <div className="flex flex-wrap justify-center gap-3 mb-10">
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={`px-5 py-2.5 rounded-full text-sm font-bold tracking-wide transition-all duration-300 ${
            active === t.key
              ? "bg-accent text-white shadow-[0_0_20px_rgba(229,9,20,0.4)] scale-105"
              : "bg-dark-800 text-gray-400 hover:bg-dark-700 hover:text-white border border-white/5 hover:border-white/10"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

/* ── Home Page ─────────────────────────────── */
export default function HomePage() {
  const [recommendations, setRecommendations] = useState([]);
  const [trending, setTrending] = useState([]);
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("all");

  useEffect(() => {
    fetch("/api/trending")
      .then((r) => r.json())
      .then((data) => { if (Array.isArray(data)) setTrending(data); })
      .catch(() => {});
  }, []);

  async function handleSelect(movie) {
    setSelectedMovie(movie);
    setLoading(true);
    try {
      const res = await fetch(`/api/recommend/${movie.id}?n=15`);
      const data = await res.json();
      setRecommendations(data);
    } catch (_) { setRecommendations([]); }
    setLoading(false);
  }

  const filteredRecs = activeTab === "all"
    ? recommendations
    : recommendations.filter((m) => m.media_type === activeTab);

  const filteredTrending = activeTab === "all"
    ? trending
    : trending.filter((m) => m.media_type === activeTab);

  return (
    <main className="min-h-screen bg-dark-900 selection:bg-accent selection:text-white">
      <section className="relative flex flex-col items-center justify-center pt-24 pb-16 px-4 overflow-hidden">
        <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] bg-accent/20 rounded-full blur-[150px] pointer-events-none" />
        <div className="absolute top-[10%] right-[10%] w-[400px] h-[400px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="text-center mb-10 relative z-10"
        >
          <div className="inline-block px-4 py-1.5 rounded-full border border-accent/30 bg-accent/10 text-accent font-semibold text-xs tracking-widest uppercase mb-6 shadow-[0_0_15px_rgba(229,9,20,0.2)]">
            AI-Powered Engine
          </div>
          <h1 className="text-6xl md:text-8xl font-black text-white mb-4 tracking-tighter drop-shadow-2xl">
            Cine<span className="text-accent">Match</span>
          </h1>
          <p className="text-gray-400 text-lg md:text-xl max-w-2xl mx-auto font-medium leading-relaxed">
            Discover thousands of movies, TV shows, and anime. Powered by advanced semantic search.
          </p>
        </motion.div>

        <div className="w-full relative z-20">
          <SearchBar onSelect={handleSelect} />
        </div>
      </section>

      <div className="px-6 md:px-16 relative z-10">
        <Tabs active={activeTab} onChange={setActiveTab} />
      </div>

      {selectedMovie && (
        <section className="px-6 md:px-16 pb-16 relative z-10">
          <div className="flex items-center gap-4 mb-8">
            <h2 className="text-3xl font-black text-white tracking-tight">
              Because you liked <span className="text-accent">{selectedMovie.title}</span>
            </h2>
            <div className="h-px bg-white/10 flex-1 mt-2"></div>
          </div>
          
          {loading ? (
            <div className="scroll-row pb-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="w-[180px] h-[270px] rounded-xl shimmer flex-shrink-0 border border-white/5" />
              ))}
            </div>
          ) : filteredRecs.length > 0 ? (
            <div className="scroll-row pb-8">
              {filteredRecs.map((m, i) => (
                <MovieCard key={`${m.id}-${m.media_type}`} movie={m} index={i} />
              ))}
            </div>
          ) : (
            <div className="bg-dark-800 border border-white/5 rounded-2xl p-12 text-center">
              <p className="text-gray-400 text-lg">No matches found for this category.</p>
            </div>
          )}
        </section>
      )}

      {filteredTrending.length > 0 && (
        <section className="px-6 md:px-16 pb-24 relative z-10">
          <div className="flex items-center gap-4 mb-8">
            <h2 className="text-3xl font-black text-white tracking-tight">🔥 Trending Now</h2>
            <div className="h-px bg-white/10 flex-1 mt-2"></div>
          </div>
          <div className="scroll-row pb-8">
            {filteredTrending.map((m, i) => (
              <MovieCard key={`${m.id}-trend`} movie={m} index={i} />
            ))}
          </div>
        </section>
      )}

      <footer className="text-center py-10 border-t border-white/5 bg-dark-900/50 relative z-10">
        <p className="text-gray-500 text-sm font-medium tracking-wider uppercase">
          Powered by Sentence-BERT & FAISS
        </p>
      </footer>
    </main>
  );
}
