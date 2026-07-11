"use client";
import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "next/navigation";
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
    <span className={`text-xs font-bold px-3 py-1 rounded-full ${c.bg} shadow-lg border border-white/5`}>
      {c.emoji} {c.label}
    </span>
  );
}

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
                style={{ background: `linear-gradient(135deg, hsl(${hue1}, 70%, 20%), hsl(${hue2}, 60%, 10%))` }}
              >
                <div className="text-3xl mb-2 opacity-50">🎥</div>
                <h3 className="font-black text-white/90 text-lg leading-tight line-clamp-4 uppercase tracking-wider">{movie.title}</h3>
              </div>
            )}
            <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm text-yellow-400 text-xs font-bold px-2 py-1 rounded-md border border-white/10">
              ⭐ {movie.rating?.toFixed(1) || "N/A"}
            </div>
            <div className="absolute top-2 left-2">
              <MediaBadge type={movie.media_type || "movie"} />
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </div>
          <p className="mt-3 text-sm font-bold text-gray-200 group-hover:text-accent transition-colors line-clamp-2">{movie.title}</p>
        </div>
      </Link>
    </motion.div>
  );
}

export default function MovieDetailPage() {
  const { id } = useParams();
  const searchParams = useSearchParams();
  const [movie, setMovie] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [backdropError, setBackdropError] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      fetch(`/api/movie/${id}`).then((r) => r.json()),
      fetch(`/api/recommend/${id}?n=15`).then((r) => r.json()),
    ]).then(([movieData, recData]) => {
      setMovie(movieData);
      setRecommendations(Array.isArray(recData) ? recData : []);
      setLoading(false);
    });
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-accent border-t-transparent rounded-full animate-spin shadow-[0_0_20px_rgba(229,9,20,0.5)]" />
      </div>
    );
  }

  if (!movie || movie.error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <div className="text-6xl mb-4">🎬</div>
        <p className="text-2xl text-gray-400 font-bold">Movie not found</p>
        <Link href="/" className="px-6 py-3 bg-accent text-white font-bold rounded-full hover:bg-accent-light transition-colors shadow-lg">← Back to Search</Link>
      </div>
    );
  }

  const trailer = movie.trailers?.[0];
  const hue1 = (movie.id * 137) % 360;
  const hue2 = (movie.id * 97) % 360;

  return (
    <main className="min-h-screen bg-dark-900">
      <section className="relative h-[70vh] overflow-hidden">
        {movie.backdrop && !backdropError ? (
          <img 
            src={movie.backdrop} 
            alt={movie.title} 
            className="w-full h-full object-cover object-top" 
            onError={() => setBackdropError(true)}
          />
        ) : (
          <div 
            className="w-full h-full"
            style={{ background: `linear-gradient(135deg, hsl(${hue1}, 70%, 15%), hsl(${hue2}, 60%, 5%))` }}
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-dark-900 via-dark-900/60 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-dark-900/90 to-transparent" />

        <div className="absolute bottom-0 left-0 right-0 p-8 md:p-16">
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}>
            <Link href="/" className="text-gray-400 hover:text-white transition-colors mb-6 inline-flex items-center gap-2 font-semibold">
              <span>←</span> Back to Search
            </Link>
            <div className="flex items-center gap-4 mb-4">
              <h1 className="text-5xl md:text-7xl font-black tracking-tight drop-shadow-2xl">{movie.title}</h1>
              <div className="hidden md:block">
                <MediaBadge type={movie.media_type || "movie"} />
              </div>
            </div>
            <div className="md:hidden mb-4"><MediaBadge type={movie.media_type || "movie"} /></div>
            
            {movie.tagline && (
              <p className="text-xl text-gray-300 italic mb-6 border-l-4 border-accent pl-4">"{movie.tagline}"</p>
            )}
            <div className="flex flex-wrap items-center gap-6 text-sm text-gray-300 mb-4 bg-black/40 backdrop-blur-md p-4 rounded-2xl w-fit border border-white/10 shadow-xl">
              <span className="flex items-center gap-2 text-yellow-400 font-black text-xl">
                ⭐ {movie.rating?.toFixed(1)}
              </span>
              <div className="w-1 h-1 bg-white/30 rounded-full" />
              {movie.release_date && <span className="font-semibold tracking-wider">{movie.release_date}</span>}
              <div className="w-1 h-1 bg-white/30 rounded-full" />
              {movie.runtime > 0 && <span className="font-semibold tracking-wider">{movie.runtime} MIN</span>}
              <div className="w-1 h-1 bg-white/30 rounded-full" />
              {movie.genres && <span className="font-semibold text-accent-light">{movie.genres}</span>}
            </div>
          </motion.div>
        </div>
      </section>

      <div className="px-8 md:px-16 -mt-8 relative z-10 space-y-20 pb-24">
        <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
          <div className="flex items-center gap-4 mb-6">
            <h2 className="text-3xl font-black">Description</h2>
            <div className="h-px bg-white/10 flex-1"></div>
          </div>
          <p className="text-gray-300 leading-relaxed max-w-4xl text-lg md:text-xl font-medium">
            {movie.overview || "No description available."}
          </p>
        </motion.section>

        {trailer && (
          <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
            <div className="flex items-center gap-4 mb-6">
              <h2 className="text-3xl font-black">🎬 Trailer</h2>
              <div className="h-px bg-white/10 flex-1"></div>
            </div>
            <div className="rounded-2xl overflow-hidden glow-red max-w-5xl aspect-video border border-accent/20">
              <iframe
                src={`https://www.youtube.com/embed/${trailer.key}`}
                title={trailer.name}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                className="w-full h-full"
              />
            </div>
          </motion.section>
        )}

        {movie.cast_details?.length > 0 && (
          <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
            <div className="flex items-center gap-4 mb-8">
              <h2 className="text-3xl font-black">🎭 Cast</h2>
              <div className="h-px bg-white/10 flex-1"></div>
            </div>
            <div className="scroll-row pb-6">
              {movie.cast_details.map((actor, i) => (
                <Link key={actor.id} href={`/cast/${actor.id}`}>
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className="group w-[150px] text-center cursor-pointer"
                  >
                    <div className="overflow-hidden rounded-full w-[130px] h-[130px] mx-auto border-[3px] border-dark-700 group-hover:border-accent transition-all duration-300 shadow-xl group-hover:shadow-[0_0_20px_rgba(229,9,20,0.4)]">
                      {actor.profile_path ? (
                        <>
                          <img 
                            src={actor.profile_path} 
                            alt={actor.name} 
                            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" 
                            onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                          />
                          <div className="w-full h-full bg-gradient-to-br from-dark-700 to-dark-800 hidden items-center justify-center text-4xl text-gray-500">👤</div>
                        </>
                      ) : (
                        <div className="w-full h-full bg-gradient-to-br from-dark-700 to-dark-800 flex items-center justify-center text-4xl text-gray-500">👤</div>
                      )}
                    </div>
                    <p className="mt-4 text-base font-bold text-gray-200 group-hover:text-white transition-colors">{actor.name}</p>
                    <p className="text-sm font-medium text-accent mt-1 line-clamp-2">{actor.character}</p>
                  </motion.div>
                </Link>
              ))}
            </div>
          </motion.section>
        )}

        {recommendations.length > 0 && (
          <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
            <div className="flex items-center gap-4 mb-8">
              <h2 className="text-3xl font-black">
                🔥 More Like <span className="text-accent">{movie.title}</span>
              </h2>
              <div className="h-px bg-white/10 flex-1"></div>
            </div>
            <div className="scroll-row pb-8">
              {recommendations.map((m, i) => (
                <MovieCard key={`${m.id}-${m.media_type}`} movie={m} index={i} />
              ))}
            </div>
          </motion.section>
        )}
      </div>
    </main>
  );
}
