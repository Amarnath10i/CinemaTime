"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";

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
            <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm text-yellow-400 text-xs font-bold px-2 py-1 rounded-md">
              ⭐ {movie.rating?.toFixed(1) || "N/A"}
            </div>
          </div>
          <p className="mt-2 text-sm font-semibold text-gray-200 group-hover:text-accent transition-colors line-clamp-2">
            {movie.title}
          </p>
        </div>
      </Link>
    </motion.div>
  );
}

export default function MovieDetailPage() {
  const { id } = useParams();
  const [movie, setMovie] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      fetch(`/api/movie/${id}`).then((r) => r.json()),
      fetch(`/api/recommend/${id}?n=15`).then((r) => r.json()),
    ]).then(([movieData, recData]) => {
      setMovie(movieData);
      setRecommendations(recData);
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

  if (!movie || movie.error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-2xl text-gray-400">Movie not found</p>
        <Link href="/" className="text-accent hover:underline">
          ← Back to Home
        </Link>
      </div>
    );
  }

  const trailer = movie.trailers?.[0];

  return (
    <main className="min-h-screen">
      {/* ── Hero Backdrop ─────────────────── */}
      <section className="relative h-[70vh] overflow-hidden">
        {movie.backdrop ? (
          <img
            src={movie.backdrop}
            alt={movie.title}
            className="w-full h-full object-cover object-top"
          />
        ) : (
          <div className="w-full h-full bg-dark-800" />
        )}
        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-dark-900 via-dark-900/60 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-dark-900/80 to-transparent" />

        {/* Movie info overlay */}
        <div className="absolute bottom-0 left-0 right-0 p-8 md:p-16">
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}>
            <Link href="/" className="text-gray-400 hover:text-white transition-colors mb-4 inline-block">
              ← Back to Search
            </Link>
            <h1 className="text-4xl md:text-6xl font-black mb-3">{movie.title}</h1>
            {movie.tagline && (
              <p className="text-lg text-gray-400 italic mb-4">"{movie.tagline}"</p>
            )}
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-300 mb-4">
              <span className="flex items-center gap-1 text-yellow-400 font-bold text-lg">
                ⭐ {movie.rating?.toFixed(1)}
              </span>
              {movie.release_date && <span>📅 {movie.release_date}</span>}
              {movie.runtime > 0 && <span>⏱ {movie.runtime} min</span>}
              {movie.genres && <span>🎭 {movie.genres}</span>}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Content ───────────────────────── */}
      <div className="px-8 md:px-16 -mt-8 relative z-10 space-y-16 pb-20">
        {/* Overview */}
        <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
          <h2 className="text-2xl font-bold mb-4">Synopsis</h2>
          <p className="text-gray-300 leading-relaxed max-w-3xl text-lg">
            {movie.overview || "No description available."}
          </p>
        </motion.section>

        {/* Trailer */}
        {trailer && (
          <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
            <h2 className="text-2xl font-bold mb-4">🎬 Trailer</h2>
            <div className="rounded-2xl overflow-hidden glow-red max-w-4xl aspect-video">
              <iframe
                src={`https://www.youtube.com/embed/${trailer.key}`}
                title={trailer.name}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                className="w-full h-full"
              />
            </div>
            {/* Additional trailers / teasers */}
            {movie.trailers?.length > 1 && (
              <div className="mt-6">
                <h3 className="text-lg font-semibold mb-3 text-gray-400">More Videos</h3>
                <div className="scroll-row">
                  {movie.trailers.slice(1).map((t) => (
                    <a
                      key={t.key}
                      href={`https://www.youtube.com/watch?v=${t.key}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="glass rounded-xl p-3 hover:border-accent/40 transition-colors w-[260px] flex-shrink-0"
                    >
                      <img
                        src={`https://img.youtube.com/vi/${t.key}/mqdefault.jpg`}
                        alt={t.name}
                        className="rounded-lg w-full h-[130px] object-cover mb-2"
                      />
                      <p className="text-sm text-gray-300 line-clamp-2">{t.name}</p>
                      <p className="text-xs text-gray-500">{t.type}</p>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </motion.section>
        )}

        {/* Cast */}
        {movie.cast_details?.length > 0 && (
          <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
            <h2 className="text-2xl font-bold mb-4">🎭 Cast</h2>
            <div className="scroll-row">
              {movie.cast_details.map((actor, i) => (
                <Link key={actor.id} href={`/cast/${actor.id}`}>
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className="group w-[140px] text-center cursor-pointer"
                  >
                    <div className="overflow-hidden rounded-full w-[110px] h-[110px] mx-auto border-2 border-transparent group-hover:border-accent transition-colors">
                      {actor.profile_path ? (
                        <img
                          src={actor.profile_path}
                          alt={actor.name}
                          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                        />
                      ) : (
                        <div className="w-full h-full bg-dark-600 flex items-center justify-center text-3xl text-gray-500">
                          👤
                        </div>
                      )}
                    </div>
                    <p className="mt-2 text-sm font-semibold text-gray-200 group-hover:text-accent transition-colors">
                      {actor.name}
                    </p>
                    <p className="text-xs text-gray-500 line-clamp-1">{actor.character}</p>
                  </motion.div>
                </Link>
              ))}
            </div>
          </motion.section>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
            <h2 className="text-2xl font-bold mb-4">
              🔥 Movies Like <span className="text-accent">{movie.title}</span>
            </h2>
            <div className="scroll-row">
              {recommendations.map((m, i) => (
                <MovieCard key={m.id} movie={m} index={i} />
              ))}
            </div>
          </motion.section>
        )}
      </div>
    </main>
  );
}
