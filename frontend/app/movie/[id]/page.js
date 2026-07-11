"use client";
import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";

function MediaBadge({ type }) {
  const config = {
    movie: { label: "MOVIE", bg: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
    tv: { label: "TV SERIES", bg: "bg-green-500/20 text-green-400 border-green-500/30" },
    anime: { label: "ANIME", bg: "bg-pink-500/20 text-pink-400 border-pink-500/30" },
  };
  const c = config[type] || config.movie;
  return (
    <span className={`text-[10px] font-bold px-3 py-1 rounded-sm border ${c.bg} uppercase tracking-[0.2em] shadow-sm`}>
      {c.label}
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
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: Math.min(i * 0.05, 0.5), duration: 0.4 }}
      className="flex-shrink-0 snap-start"
    >
      <Link href={`/movie/${movie.id}?type=${movie.media_type || "movie"}`}>
        <div className="group relative w-[200px] cursor-pointer">
          <div className="overflow-hidden rounded-md h-[300px] bg-dark-800 relative shadow-lg group-hover:shadow-[0_8px_30px_rgba(229,9,20,0.3)] transition-all duration-300 transform group-hover:-translate-y-2">
            {poster ? (
              <img 
                src={poster} 
                alt={movie.title} 
                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" 
                onError={() => setImageError(true)}
              />
            ) : (
              <div 
                className="w-full h-full flex flex-col items-center justify-center p-4 text-center transition-transform duration-700 group-hover:scale-105"
                style={{ background: `linear-gradient(135deg, hsl(${hue1}, 70%, 20%), hsl(${hue2}, 60%, 10%))` }}
              >
                <h3 className="font-black text-white/90 text-lg leading-tight line-clamp-4 uppercase tracking-wider">{movie.title}</h3>
              </div>
            )}
            <div className="absolute top-2 right-2 bg-black/80 backdrop-blur-md text-white text-[10px] font-bold px-1.5 py-0.5 rounded border border-white/10">
              {movie.rating?.toFixed(1) || "N/A"}
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-4">
               <p className="text-sm font-bold text-white line-clamp-2 leading-tight">{movie.title}</p>
            </div>
          </div>
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
  const [showTrailer, setShowTrailer] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    window.scrollTo(0, 0);
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
        <div className="w-16 h-16 border-[3px] border-dark-700 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!movie || movie.error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-2xl text-gray-500 font-bold font-outfit uppercase tracking-widest">Title Not Found</p>
        <Link href="/" className="px-6 py-3 bg-white text-black font-bold rounded hover:bg-gray-200 transition-colors">Return Home</Link>
      </div>
    );
  }

  const trailer = movie.trailers?.[0];
  const hue1 = (movie.id * 137) % 360;
  const hue2 = (movie.id * 97) % 360;

  return (
    <main className="min-h-screen bg-dark-900 pb-24">
      {/* Immersive Header */}
      <section className="relative h-[85vh] w-full overflow-hidden flex items-end">
        <div className="absolute inset-0 z-0">
          {movie.backdrop && !backdropError ? (
            <img 
              src={movie.backdrop} 
              alt={movie.title} 
              className="w-full h-full object-cover object-top opacity-50" 
              onError={() => setBackdropError(true)}
            />
          ) : (
            <div 
              className="w-full h-full opacity-50"
              style={{ background: `linear-gradient(135deg, hsl(${hue1}, 70%, 15%), hsl(${hue2}, 60%, 5%))` }}
            />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-dark-900 via-dark-900/60 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-dark-900 via-dark-900/40 to-transparent" />
        </div>

        <div className="relative z-10 w-full px-6 md:px-12 pb-16 flex flex-col md:flex-row gap-10 items-end">
          <motion.div 
            initial={{ opacity: 0, y: 50 }} 
            animate={{ opacity: 1, y: 0 }}
            className="hidden md:block flex-shrink-0"
          >
            <div className="w-[280px] rounded-lg overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.5)] border border-white/10">
               {movie.poster && !movie.poster.includes("placeholder") ? (
                 <img src={movie.poster} alt={movie.title} className="w-full h-auto" />
               ) : (
                 <div className="w-full h-[420px]" style={{ background: `linear-gradient(135deg, hsl(${hue1}, 70%, 20%), hsl(${hue2}, 60%, 10%))` }} />
               )}
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} className="flex-1">
            <div className="mb-4">
              <MediaBadge type={movie.media_type || "movie"} />
            </div>
            <h1 className="text-5xl md:text-7xl font-black tracking-tighter uppercase font-outfit leading-none mb-4 drop-shadow-lg">
              {movie.title}
            </h1>
            
            <div className="flex flex-wrap items-center gap-4 text-sm font-semibold tracking-wide text-gray-300 mb-6">
              <span className="text-white bg-white/10 px-2 py-1 rounded">MATCH {Math.round((movie.rating || 0) * 10)}%</span>
              {movie.release_date && <span>{movie.release_date.slice(0, 4)}</span>}
              {movie.runtime > 0 && <span>{movie.runtime}M</span>}
            </div>

            <p className="text-lg md:text-xl text-gray-300 leading-relaxed max-w-3xl font-medium drop-shadow-md">
              {movie.overview || "No description available."}
            </p>

            <div className="flex flex-wrap items-center gap-6 mt-6 text-sm text-gray-300">
               {movie.genres && (
                 <div>
                   <span className="text-gray-500 font-semibold uppercase tracking-wider text-xs mr-2">Genres:</span>
                   <span className="text-gray-200">{movie.genres}</span>
                 </div>
               )}
               {movie.tagline && (
                 <div>
                   <span className="text-gray-500 font-semibold uppercase tracking-wider text-xs mr-2">Tagline:</span>
                   <span className="text-gray-200 italic">"{movie.tagline}"</span>
                 </div>
               )}
            </div>

            <div className="mt-8 flex gap-4">
              {trailer && (
                <button 
                  onClick={() => setShowTrailer(true)}
                  className="bg-white text-black px-8 py-3 rounded font-bold text-lg hover:bg-gray-200 transition-colors flex items-center gap-2 shadow-[0_0_20px_rgba(255,255,255,0.3)]"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                  Play Trailer
                </button>
              )}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Cast Section */}
      <div className="px-6 md:px-12 mt-8">
        {movie.cast_details?.length > 0 && (
          <div className="glass rounded-2xl p-8 flex flex-col justify-start overflow-hidden">
            <h3 className="text-2xl font-bold font-outfit mb-6 text-white">Cast</h3>
            <div className="scroll-row !pb-4 !pt-2">
              {movie.cast_details.slice(0, 15).map(actor => (
                <Link key={actor.id} href={`/cast/${actor.id}`}>
                  <div className="flex flex-col items-center gap-3 group cursor-pointer w-[120px] flex-shrink-0 snap-start">
                    <div className="w-24 h-24 rounded-full overflow-hidden bg-dark-700 shadow-md border-2 border-white/10 group-hover:border-[#00b4ff] transition-all duration-300">
                       {actor.profile_path ? (
                         <img src={actor.profile_path} alt={actor.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                       ) : (
                         <div className="w-full h-full flex items-center justify-center text-3xl">👤</div>
                       )}
                    </div>
                    <div className="text-center w-full">
                      <p className="text-[14px] font-bold text-gray-200 group-hover:text-white transition-colors line-clamp-1">{actor.name}</p>
                      <p className="text-[12px] text-[#00b4ff] font-medium line-clamp-1 mt-0.5">{actor.character}</p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Recommendations Row */}
      {recommendations.length > 0 && (
        <div className="px-6 md:px-12 mt-16">
          <h2 className="text-2xl font-bold font-outfit mb-4 text-white">More Like This</h2>
          <div className="scroll-row">
            {recommendations.map((m, i) => (
              <MovieCard key={`${m.id}-${m.media_type}`} movie={m} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Fullscreen Trailer Modal */}
      <AnimatePresence>
        {showTrailer && trailer && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9999] bg-black flex items-center justify-center"
          >
            <button 
              onClick={() => setShowTrailer(false)}
              className="absolute top-6 right-6 p-4 rounded-full bg-black/50 hover:bg-black/80 text-white transition-colors z-[10000] border border-white/20"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="w-full h-full bg-black relative"
            >
              <iframe
                src={`https://www.youtube.com/embed/${trailer.key}?autoplay=1`}
                title={trailer.name}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                className="w-full h-full absolute inset-0"
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </main>
  );
}
