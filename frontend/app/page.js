"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

/* ── Media Badge ───────────────────────────── */
function MediaBadge({ type }) {
  const config = {
    movie: { label: "MOVIE", bg: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
    tv: { label: "TV SERIES", bg: "bg-green-500/20 text-green-400 border-green-500/30" },
    anime: { label: "ANIME", bg: "bg-pink-500/20 text-pink-400 border-pink-500/30" },
  };
  const c = config[type] || config.movie;
  return (
    <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${c.bg} tracking-widest uppercase shadow-sm`}>
      {c.label}
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
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: Math.min(i * 0.05, 0.5), duration: 0.4 }}
      className="flex-shrink-0 snap-start"
    >
      <Link href={`/movie/${movie.id}?type=${movie.media_type || "movie"}`}>
        <div className="group relative w-[200px] cursor-pointer">
          <div className="overflow-hidden rounded-md h-[300px] bg-dark-800 relative shadow-[0_4px_20px_rgba(0,0,0,0.5)] group-hover:shadow-[0_8px_30px_rgba(229,9,20,0.3)] transition-all duration-300 transform group-hover:-translate-y-2">
            
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
                style={{
                  background: `linear-gradient(135deg, hsl(${hue1}, 70%, 20%), hsl(${hue2}, 60%, 10%))`
                }}
              >
                <h3 className="font-black text-white/90 text-lg leading-tight line-clamp-4 uppercase tracking-wider font-outfit">{movie.title}</h3>
              </div>
            )}

            <div className="absolute top-2 right-2 bg-black/80 backdrop-blur-md text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow-md border border-white/10">
              {movie.rating?.toFixed(1) || "N/A"}
            </div>
            
            <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-4">
               <MediaBadge type={movie.media_type || "movie"} />
               <p className="mt-2 text-sm font-bold text-white line-clamp-2 leading-tight">{movie.title}</p>
               {movie.release_date && (
                 <p className="text-xs text-gray-400 mt-1">{movie.release_date.slice(0, 4)}</p>
               )}
            </div>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}

/* ── Hero Carousel ─────────────────────────────── */
function HeroCarousel({ items }) {
  const [current, setCurrent] = useState(0);
  const [activeDetails, setActiveDetails] = useState(null);

  // Rotate carousel every 15 seconds (enough time to watch a bit of the trailer)
  useEffect(() => {
    if (!items || items.length === 0) return;
    const interval = setInterval(() => {
      setCurrent((c) => (c + 1) % Math.min(items.length, 5));
    }, 15000);
    return () => clearInterval(interval);
  }, [items]);

  // Fetch trailer/backdrop for the active slide
  useEffect(() => {
    if (!items || items.length === 0) return;
    const movie = items[current];
    setActiveDetails(null); // Clear previous trailer while fetching
    fetch(`/api/movie/${movie.id}`)
      .then(r => r.json())
      .then(data => {
        if (!data.error) setActiveDetails(data);
      })
      .catch(() => setActiveDetails(null));
  }, [current, items]);

  if (!items || items.length === 0) return <div className="h-[85vh] bg-dark-900 animate-pulse" />;

  const baseMovie = items[current];
  const movie = activeDetails || baseMovie;
  const trailer = movie.trailers?.[0];
  const backdrop = movie.backdrop || baseMovie.backdrop || baseMovie.poster;
  const isPlaceholder = !backdrop || backdrop.includes("placeholder");

  return (
    <div className="relative h-[85vh] w-full overflow-hidden bg-dark-900">
      <AnimatePresence mode="wait">
        <motion.div
          key={baseMovie.id}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.2 }}
          className="absolute inset-0"
        >
          {trailer ? (
            <div className="w-full h-full scale-[1.35] md:scale-[1.15] pointer-events-none opacity-80">
              <iframe
                src={`https://www.youtube.com/embed/${trailer.key}?autoplay=1&mute=1&controls=0&showinfo=0&rel=0&loop=1&playlist=${trailer.key}`}
                allow="autoplay; encrypted-media"
                className="w-full h-full"
              />
            </div>
          ) : !isPlaceholder ? (
             <img src={backdrop} alt={movie.title} className="w-full h-full object-cover object-top opacity-60" />
          ) : (
             <div className="w-full h-full bg-dark-800" />
          )}
          
          <div className="absolute inset-0 bg-gradient-to-t from-dark-900 via-dark-900/40 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-dark-900 via-dark-900/60 to-transparent" />
        </motion.div>
      </AnimatePresence>

      <div className="absolute inset-0 flex items-center">
        <div className="px-6 md:px-12 w-full">
          <motion.div
            key={`text-${baseMovie.id}`}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.8 }}
          >
            <div className="mb-4">
              <span className="text-[10px] font-bold px-3 py-1 rounded-sm border bg-blue-500/20 text-blue-400 border-blue-500/30 uppercase tracking-[0.2em]">
                {baseMovie.media_type || "movie"}
              </span>
            </div>
            <h1 className="text-5xl md:text-8xl font-black tracking-tighter uppercase font-outfit leading-none mb-4 drop-shadow-lg text-white max-w-4xl line-clamp-2">
              {movie.title || baseMovie.title}
            </h1>
            <p className="text-gray-300 text-lg md:text-xl font-medium max-w-2xl line-clamp-3 mb-8 drop-shadow-md">
              {movie.overview || baseMovie.overview || "Explore this trending title on CinemaTime."}
            </p>
            <div className="flex gap-4">
              <Link href={`/movie/${baseMovie.id}?type=${baseMovie.media_type}`}>
                <button className="bg-white text-black px-8 py-3 rounded font-bold text-lg hover:bg-gray-200 transition-colors flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                  More Info
                </button>
              </Link>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

/* ── Home Page ─────────────────────────────── */
export default function HomePage() {
  const [trending, setTrending] = useState([]);
  const [loading, setLoading] = useState(true);
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") || "all";

  useEffect(() => {
    fetch("/api/trending")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) setTrending(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const filteredTrending = tab === "all"
    ? trending
    : trending.filter((m) => m.media_type === tab);

  // Group into custom rows based on genres for a Netflix feel
  const actionRow = filteredTrending.filter(m => m.id % 2 === 0);
  const dramaRow = filteredTrending.filter(m => m.id % 2 !== 0);

  return (
    <main className="min-h-screen bg-dark-900 selection:bg-accent selection:text-white pb-20">
      
      <HeroCarousel items={filteredTrending} />

      <div className="px-6 md:px-12 -mt-12 relative z-20 space-y-12">
        
        {loading ? (
          <div className="scroll-row">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="w-[200px] h-[300px] rounded-md bg-dark-800 animate-pulse flex-shrink-0" />
            ))}
          </div>
        ) : filteredTrending.length > 0 ? (
          <>
            <section>
              <h2 className="text-2xl font-bold text-white mb-4 px-2 font-outfit">Top Trending Now</h2>
              <div className="scroll-row">
                {filteredTrending.map((m, i) => (
                  <MovieCard key={`${m.id}-t1`} movie={m} index={i} />
                ))}
              </div>
            </section>

            {actionRow.length > 0 && (
              <section>
                <h2 className="text-2xl font-bold text-white mb-4 px-2 font-outfit">Action & Adventure</h2>
                <div className="scroll-row">
                  {actionRow.map((m, i) => (
                    <MovieCard key={`${m.id}-a`} movie={m} index={i} />
                  ))}
                </div>
              </section>
            )}

            {dramaRow.length > 0 && (
              <section>
                <h2 className="text-2xl font-bold text-white mb-4 px-2 font-outfit">Critically Acclaimed</h2>
                <div className="scroll-row">
                  {dramaRow.map((m, i) => (
                    <MovieCard key={`${m.id}-d`} movie={m} index={i} />
                  ))}
                </div>
              </section>
            )}
          </>
        ) : (
          <div className="pt-24 text-center">
            <p className="text-gray-500 text-xl">No content available for this category.</p>
          </div>
        )}
      </div>

    </main>
  );
}
