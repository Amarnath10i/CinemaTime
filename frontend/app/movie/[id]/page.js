"use client";
import { useState, useEffect, Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import { MovieCard, idHues } from "../../../components/MovieCard";
import { TrailerModal } from "../../../components/TrailerModal";
import { youtubeThumb, youtubeSearchUrl } from "../../../components/TrailerPlayer";

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

function MovieDetailContent() {
  const { id } = useParams();
  const searchParams = useSearchParams();
  // Movie and TV ids overlap on TMDB, so the backend needs the type to pick the right title.
  const type = searchParams.get("type") || "";
  const [movie, setMovie] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [backdropError, setBackdropError] = useState(false);
  const [videoIndex, setVideoIndex] = useState(null); // index into movie.trailers while the player is open

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setVideoIndex(null);
    window.scrollTo(0, 0);
    const typeQuery = type ? `?type=${encodeURIComponent(type)}` : "";
    Promise.all([
      fetch(`/api/movie/${id}${typeQuery}`).then((r) => r.json()).catch(() => null),
      fetch(`/api/recommend/${id}?n=15`).then((r) => r.json()).catch(() => []),
    ]).then(([movieData, recData]) => {
      setMovie(movieData);
      setRecommendations(Array.isArray(recData) ? recData : []);
      setLoading(false);
    });
  }, [id, type]);

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

  const trailers = movie.trailers || [];
  const year = movie.release_date?.slice(0, 4) || "";
  const [hue1, hue2] = idHues(movie.id);

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

            <div className="mt-8 flex flex-wrap gap-4">
              {trailers.length > 0 ? (
                <button
                  onClick={() => setVideoIndex(0)}
                  className="bg-white text-black px-8 py-3 rounded font-bold text-lg hover:bg-gray-200 transition-colors flex items-center gap-2 shadow-[0_0_20px_rgba(255,255,255,0.3)]"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                  Play {trailers[0].type || "Trailer"}
                </button>
              ) : (
                <a
                  href={youtubeSearchUrl(movie.title, year)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-white/10 text-white px-8 py-3 rounded font-bold text-lg hover:bg-white/20 transition-colors flex items-center gap-2 border border-white/20"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                  Find Trailer on YouTube
                </a>
              )}
              {trailers.length > 1 && (
                <a href="#videos" className="px-6 py-3 rounded font-bold text-lg text-white bg-white/10 hover:bg-white/20 border border-white/20 transition-colors">
                  {trailers.length} Videos
                </a>
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

      {/* Trailers, teasers and clips */}
      {trailers.length > 0 && (
        <div id="videos" className="px-6 md:px-12 mt-8 scroll-mt-24">
          <h2 className="text-2xl font-bold font-outfit mb-4 text-white">Trailers &amp; Videos</h2>
          <div className="scroll-row">
            {trailers.map((v, i) => (
              <button
                key={v.key}
                onClick={() => setVideoIndex(i)}
                className="group flex-shrink-0 snap-start w-[260px] md:w-[300px] text-left"
              >
                <div className="relative aspect-video rounded-md overflow-hidden bg-dark-800 shadow-lg">
                  <img src={youtubeThumb(v.key)} alt="" loading="lazy" className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
                  <div className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover:bg-black/10 transition-colors">
                    <span className="w-12 h-12 rounded-full bg-black/70 border border-white/30 flex items-center justify-center text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 3 20 12 6 21 6 3"></polygon></svg>
                    </span>
                  </div>
                  <span className="absolute top-2 left-2 text-[9px] font-bold uppercase tracking-wider bg-black/80 text-white px-1.5 py-0.5 rounded">{v.type}</span>
                </div>
                <p className="mt-2 text-sm text-gray-300 group-hover:text-white line-clamp-2 leading-snug">{v.name}</p>
              </button>
            ))}
          </div>
        </div>
      )}

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

      <TrailerModal
        open={videoIndex !== null}
        videos={trailers}
        startIndex={videoIndex ?? 0}
        title={movie.title}
        year={year}
        onClose={() => setVideoIndex(null)}
      />

    </main>
  );
}

export default function MovieDetailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-dark-900">
        <div className="w-16 h-16 border-[3px] border-dark-700 border-t-accent rounded-full animate-spin" />
      </div>
    }>
      <MovieDetailContent />
    </Suspense>
  );
}
