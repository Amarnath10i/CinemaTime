"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";

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

function MovieCard({ movie, index: i }) {
  const poster = movie.poster?.includes("tmdb.org")
    ? movie.poster
    : movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : movie.poster || "https://via.placeholder.com/500x750?text=No+Poster";

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.04, duration: 0.4 }}
    >
      <Link href={`/movie/${movie.id}?type=${movie.media_type || "movie"}`}>
        <div className="group relative w-[180px] cursor-pointer">
          <div className="overflow-hidden rounded-xl">
            <img src={poster} alt={movie.title} className="w-full h-[270px] object-cover transition-transform duration-500 group-hover:scale-110" />
            <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm text-yellow-400 text-xs font-bold px-2 py-1 rounded-md">
              ⭐ {movie.rating?.toFixed(1) || "N/A"}
            </div>
            <div className="absolute top-2 left-2">
              <MediaBadge type={movie.media_type || "movie"} />
            </div>
          </div>
          <p className="mt-2 text-sm font-semibold text-gray-200 group-hover:text-accent transition-colors line-clamp-2">{movie.title}</p>
          <p className="text-xs text-accent mt-1 line-clamp-1">{movie.character}</p>
        </div>
      </Link>
    </motion.div>
  );
}

export default function CastDetailPage() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    fetch(`/api/cast/${id}/movies`)
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!data || data.error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-2xl text-gray-400">Actor not found</p>
      </div>
    );
  }

  const { person, movies } = data;

  return (
    <main className="min-h-screen pt-24 px-8 md:px-16 pb-20">
      <Link href="/" className="text-gray-400 hover:text-white transition-colors mb-8 inline-block">
        ← Back to Search
      </Link>

      <div className="flex flex-col md:flex-row gap-12 mb-16">
        <div className="flex-shrink-0">
          <div className="w-[200px] md:w-[300px] rounded-2xl overflow-hidden glow-red">
            {person.profile_path ? (
              <img src={person.profile_path} alt={person.name} className="w-full object-cover" />
            ) : (
              <div className="w-full h-[450px] bg-dark-700 flex items-center justify-center text-6xl">👤</div>
            )}
          </div>
        </div>
        
        <div className="flex-1">
          <h1 className="text-5xl font-black mb-4">{person.name}</h1>
          <div className="flex flex-wrap gap-4 text-sm text-gray-400 mb-6">
            {person.birthday && <span>🎂 {person.birthday}</span>}
            {person.place_of_birth && <span>📍 {person.place_of_birth}</span>}
          </div>
          
          {person.biography ? (
            <div>
              <h3 className="text-xl font-bold mb-3">Biography</h3>
              <p className="text-gray-300 leading-relaxed whitespace-pre-line">
                {person.biography}
              </p>
            </div>
          ) : (
            <p className="text-gray-500 italic">No biography available.</p>
          )}
        </div>
      </div>

      <section>
        <h2 className="text-3xl font-bold mb-8">Filmography</h2>
        <div className="flex flex-wrap gap-6 justify-center md:justify-start">
          {movies?.map((m, i) => (
            <MovieCard key={`${m.id}-${m.media_type}`} movie={m} index={i} />
          ))}
        </div>
      </section>
    </main>
  );
}
