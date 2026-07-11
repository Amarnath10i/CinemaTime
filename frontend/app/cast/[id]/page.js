"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";

export default function CastPage() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetch(`/api/cast/${id}/movies`)
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
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
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-2xl text-gray-400">Actor not found</p>
        <Link href="/" className="text-accent hover:underline">← Back to Home</Link>
      </div>
    );
  }

  const person = data.person;
  const movies = data.movies;

  return (
    <main className="min-h-screen px-8 md:px-16 py-12">
      {/* Back link */}
      <Link href="/" className="text-gray-400 hover:text-white transition-colors mb-8 inline-block">
        ← Back to Search
      </Link>

      {/* ── Actor Profile ─────────────────── */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col md:flex-row gap-8 mb-16"
      >
        {/* Profile photo */}
        <div className="flex-shrink-0">
          {person.profile_path ? (
            <img
              src={person.profile_path}
              alt={person.name}
              className="w-[220px] h-[330px] object-cover rounded-2xl glow-red"
            />
          ) : (
            <div className="w-[220px] h-[330px] bg-dark-700 rounded-2xl flex items-center justify-center text-6xl text-gray-600">
              👤
            </div>
          )}
        </div>

        {/* Bio */}
        <div className="flex-1">
          <h1 className="text-4xl md:text-5xl font-black mb-4">
            <span className="bg-gradient-to-r from-accent to-accent-light bg-clip-text text-transparent">
              {person.name}
            </span>
          </h1>
          {person.birthday && (
            <p className="text-gray-400 mb-1">🎂 Born: {person.birthday}</p>
          )}
          {person.place_of_birth && (
            <p className="text-gray-400 mb-4">📍 {person.place_of_birth}</p>
          )}
          {person.biography && (
            <p className="text-gray-300 leading-relaxed max-w-3xl line-clamp-[8]">
              {person.biography}
            </p>
          )}
        </div>
      </motion.section>

      {/* ── Filmography ───────────────────── */}
      <section>
        <h2 className="text-2xl font-bold mb-6">🎬 Filmography</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-6">
          {movies.map((movie, i) => (
            <motion.div
              key={movie.id}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03, duration: 0.4 }}
            >
              <Link href={`/movie/${movie.id}`}>
                <div className="group cursor-pointer">
                  <div className="overflow-hidden rounded-xl relative">
                    <img
                      src={movie.poster}
                      alt={movie.title}
                      className="w-full h-[240px] object-cover transition-transform duration-500 group-hover:scale-110"
                    />
                    <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm text-yellow-400 text-xs font-bold px-2 py-1 rounded-md">
                      ⭐ {movie.rating?.toFixed(1) || "N/A"}
                    </div>
                  </div>
                  <p className="mt-2 text-sm font-semibold text-gray-200 group-hover:text-accent transition-colors line-clamp-2">
                    {movie.title}
                  </p>
                  {movie.character && (
                    <p className="text-xs text-gray-500">as {movie.character}</p>
                  )}
                  {movie.release_date && (
                    <p className="text-xs text-gray-600">{movie.release_date?.slice(0, 4)}</p>
                  )}
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>
    </main>
  );
}
