"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { MovieCard } from "../../components/MovieCard";
import { useLikes } from "../../components/likes";

const KIND_STYLE = {
  collaborative: "text-[#00b4ff]",
  new: "text-[#00ff66]",
  content: "text-[#ffcc00]",
  popular: "text-gray-400",
};

function SmallHeart({ liked, onClick, title }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={liked}
      aria-label={liked ? `Unlike ${title}` : `Like ${title}`}
      className="shrink-0 p-1 rounded hover:bg-white/10 transition-colors"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill={liked ? "#ff0066" : "none"}
        stroke={liked ? "#ff0066" : "currentColor"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
      </svg>
    </button>
  );
}

export default function ForYouPage() {
  const { likes, isLiked, toggle, clear } = useLikes();
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  const likedIds = likes.map((m) => m.id).join(",");

  useEffect(() => {
    if (query.length < 2) { setSuggestions([]); return; }
    const timer = setTimeout(() => {
      fetch(`/api/movies/titles?q=${encodeURIComponent(query)}`)
        .then((r) => r.json())
        .then((data) => setSuggestions((Array.isArray(data) ? data : []).filter((s) => s.media_type === "movie").slice(0, 12)))
        .catch(() => setSuggestions([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      fetch("/api/for-you", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ liked: likedIds ? likedIds.split(",") : [], n: 24 }),
      })
        .then((r) => r.json())
        .then(setResult)
        .catch(() => setResult({ available: false, items: [] }))
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [likedIds]);

  const items = result?.items || [];
  const cold = likes.length === 0;

  return (
    <main className="min-h-screen bg-dark-900 pb-20 pt-28 px-6 md:px-12">
      <div className="max-w-7xl mx-auto">
        <div className="mb-10">
          <h1 className="text-4xl md:text-6xl font-black font-outfit uppercase tracking-tighter text-white">
            For <span className="text-[#00b4ff]">You</span>
          </h1>
          <p className="text-gray-400 mt-3 max-w-3xl text-lg">
            Ranked from the movies you like by a model trained on 32 million MovieLens ratings: four
            retrievers propose candidates and a learning-to-rank model orders them.{" "}
            <Link href="/how-it-works" className="text-[#00b4ff] hover:underline whitespace-nowrap">How it works →</Link>
          </p>
        </div>

        <section className="glass rounded-2xl p-6 mb-10">
          <div className="flex flex-col md:flex-row md:items-center gap-4 justify-between">
            <h2 className="text-xl font-bold font-outfit">
              Movies you like <span className="text-gray-500 font-normal">({likes.length})</span>
            </h2>
            <div className="relative w-full md:w-96">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Add a movie you like..."
                className="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-[#00b4ff] transition-colors"
              />
              {suggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-dark-800 border border-white/10 rounded-lg shadow-2xl max-h-72 overflow-y-auto z-50">
                  {suggestions.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => { if (!isLiked(s.id)) toggle(s); setQuery(""); setSuggestions([]); }}
                      className="w-full text-left px-4 py-2 hover:bg-white/10 text-sm border-b border-white/5 last:border-0 flex justify-between items-center"
                    >
                      <span className="line-clamp-1">{s.title}</span>
                      {isLiked(s.id) && <span className="text-xs text-[#ff0066]">Liked</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {likes.length > 0 ? (
            <div className="flex flex-wrap gap-2 mt-5">
              {likes.map((m) => (
                <span key={m.id} className="flex items-center gap-2 bg-black/40 border border-white/10 rounded-full pl-4 pr-2 py-1.5 text-sm">
                  <Link href={`/movie/${m.id}?type=movie`} className="hover:text-white text-gray-200 line-clamp-1 max-w-[220px]">{m.title}</Link>
                  <button onClick={() => toggle(m)} className="text-gray-500 hover:text-white px-1" aria-label={`Remove ${m.title}`}>✕</button>
                </span>
              ))}
              <button onClick={clear} className="text-xs uppercase tracking-wider text-gray-500 hover:text-white ml-2">Clear all</button>
            </div>
          ) : (
            <p className="text-gray-500 text-sm mt-4">
              Nothing yet. Heart a few movies below or on any movie page; five is plenty to get started.
            </p>
          )}
          {result?.ignored?.length > 0 && (
            <p className="text-xs text-gray-500 mt-3">
              {result.ignored.length} liked title{result.ignored.length > 1 ? "s are" : " is"} outside the trained catalog and not used.
            </p>
          )}
        </section>

        <h2 className="text-2xl font-bold font-outfit mb-6 text-white">
          {cold ? "Start with a few favourites" : "Recommended for you"}
        </h2>

        {loading && items.length === 0 ? (
          <div className="flex justify-center py-20">
            <div className="w-12 h-12 border-[3px] border-dark-700 border-t-[#00b4ff] rounded-full animate-spin" />
          </div>
        ) : result && !result.available ? (
          <p className="text-gray-400">
            The personalized model is not deployed on this server yet (run <code>uv run cinemaml export</code> in <code>ml/</code>).
          </p>
        ) : (
          <div className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-x-4 gap-y-8 transition-opacity ${loading ? "opacity-50" : ""}`}>
            {items.map((m, i) => (
              <div key={m.id} className="flex flex-col">
                <MovieCard movie={{ ...m, explanation: undefined }} index={i} />
                <div className="flex items-start justify-between gap-1 mt-2 max-w-[200px]">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-gray-200 line-clamp-1">{m.title}</p>
                    <p className={`text-xs leading-snug line-clamp-2 ${KIND_STYLE[m.explanation?.kind] || "text-gray-400"}`}>
                      {m.explanation?.reason}
                    </p>
                  </div>
                  <SmallHeart liked={isLiked(m.id)} onClick={() => toggle(m)} title={m.title} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
