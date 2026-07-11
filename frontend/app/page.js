"use client";
import { useState, useEffect, Suspense } from "react";
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
  const [showTrailer, setShowTrailer] = useState(false);

  // Rotate carousel every 20 seconds
  useEffect(() => {
    if (!items || items.length === 0) return;
    const interval = setInterval(() => {
      setCurrent((c) => (c + 1) % Math.min(items.length, 5));
    }, 20000);
    return () => clearInterval(interval);
  }, [items]);

  // Fetch trailer/backdrop for the active slide
  useEffect(() => {
    if (!items || items.length === 0) return;
    const movie = items[current];
    setActiveDetails(null); // Clear previous trailer while fetching
    setShowTrailer(false); // Reset trailer view
    fetch(`/api/movie/${movie.id}`)
      .then(r => r.json())
      .then(data => {
        if (!data.error) setActiveDetails(data);
      })
      .catch(() => setActiveDetails(null));
  }, [current, items]);

  // Trigger trailer fade-in after 4 seconds if trailer is available
  useEffect(() => {
    let timer;
    if (activeDetails && activeDetails.trailers && activeDetails.trailers.length > 0) {
      const trailerKey = activeDetails.trailers[0].key;
      
      // Check if video is deleted/private by loading its thumbnail
      const img = new Image();
      img.src = `https://img.youtube.com/vi/${trailerKey}/mqdefault.jpg`;
      
      img.onload = () => {
        // YouTube returns a 120x90 placeholder image for unavailable videos
        if (img.width !== 120) {
          timer = setTimeout(() => {
            setShowTrailer(true);
          }, 4000);
        }
      };
      // If it 404s, it's also unavailable (doesn't trigger onload)
    }
    return () => clearTimeout(timer);
  }, [activeDetails]);

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
          {/* Backdrop Image - fades out when trailer shows */}
          {!isPlaceholder && (
            <img 
              src={backdrop} 
              alt={movie.title} 
              className={`absolute inset-0 w-full h-full object-cover object-top transition-opacity duration-1000 ${showTrailer ? 'opacity-0' : 'opacity-60'}`} 
            />
          )}
          {isPlaceholder && <div className="absolute inset-0 w-full h-full bg-dark-800" />}

          {/* Trailer Video - fades in when showTrailer is true, completely bright */}
          {trailer && (
            <div className={`absolute inset-0 w-full h-full overflow-hidden pointer-events-none transition-opacity duration-1000 ${showTrailer ? 'opacity-100' : 'opacity-0'}`}>
              <iframe
                src={`https://www.youtube.com/embed/${trailer.key}?autoplay=1&mute=1&controls=0&showinfo=0&rel=0&loop=1&playlist=${trailer.key}&cc_load_policy=1&cc_lang_pref=zz&iv_load_policy=3&modestbranding=1&playsinline=1&disablekb=1`}
                allow="autoplay; encrypted-media"
                className="absolute top-1/2 left-1/2 w-[100vw] h-[56.25vw] min-h-[85vh] min-w-[151.11vh] -translate-x-1/2 -translate-y-1/2 pointer-events-none"
              />
            </div>
          )}
          
          {/* Gradients fade out completely to 0% so video is 100% bright */}
          <div className={`absolute inset-0 bg-gradient-to-t from-dark-900 via-dark-900/40 to-transparent transition-opacity duration-1000 ${showTrailer ? 'opacity-0' : 'opacity-100'}`} />
          <div className={`absolute inset-0 bg-gradient-to-r from-dark-900 via-dark-900/60 to-transparent transition-opacity duration-1000 ${showTrailer ? 'opacity-0' : 'opacity-100'}`} />
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
            <div className={`transition-opacity duration-1000 ${showTrailer ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>
              <div className="mb-4">
                <span className="text-[10px] font-bold px-3 py-1 rounded-sm border bg-blue-500/20 text-blue-400 border-blue-500/30 uppercase tracking-[0.2em]">
                  {baseMovie.media_type || "movie"}
                </span>
              </div>
              
              <h1 className="font-black tracking-tighter uppercase font-outfit leading-none drop-shadow-lg text-white max-w-4xl line-clamp-2 text-5xl md:text-8xl mb-8">
                {movie.title || baseMovie.title}
              </h1>
              
              <div className="flex gap-4">
                <Link href={`/movie/${baseMovie.id}?type=${baseMovie.media_type}`}>
                  <button className="bg-white text-black px-8 py-3 rounded font-bold text-lg hover:bg-gray-200 transition-all duration-1000 flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    More Info
                  </button>
                </Link>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

/* ── Home Page ─────────────────────────────── */
function HomeContent() {
  const [trending, setTrending] = useState([]);
  const [categoryData, setCategoryData] = useState({});
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

    let categories = ["Action", "Adventure", "Horror", "Thriller", "Romance", "Science Fiction", "Mystery", "Comedy"];
    
    if (tab === "tv") {
      categories = ["Action & Adventure", "Sci-Fi & Fantasy", "Comedy", "Drama", "Mystery", "Crime", "Animation"];
    } else if (tab === "anime") {
      categories = ["Animation", "Action", "Fantasy", "Sci-Fi & Fantasy"];
    }

    const fetchCategories = async () => {
      const data = {};
      await Promise.all(
        categories.map(async (cat) => {
          try {
            // If anime, we don't pass media_type=anime because TMDB uses movie/tv
            const typeQuery = (tab !== "all" && tab !== "anime") ? `&media_type=${tab}` : "";
            const res = await fetch(`/api/movies/category/${encodeURIComponent(cat)}?n=15${typeQuery}`);
            const json = await res.json();
            if (Array.isArray(json) && json.length > 0) {
              data[cat] = json;
            }
          } catch (e) {
            console.error(`Error fetching category ${cat}`, e);
          }
        })
      );
      setCategoryData(data);
    };
    fetchCategories();
  }, [tab]);

  const filteredTrending = tab === "all"
    ? trending
    : tab === "anime"
    ? trending.filter((m) => (m.title && m.title.toLowerCase().match(/anime|no hero|jujutsu|demon slayer|attack on titan|naruto|one piece|bleach|dragon ball/)))
    : trending.filter((m) => m.media_type === tab);

  const filteredCategories = {};
  Object.entries(categoryData).forEach(([cat, movies]) => {
    let filtered = movies;
    if (tab === "anime") {
      // For anime, we only want things that are animated or anime-like
      filtered = movies.filter((m) => (m.genres || "").includes("Animation") || cat === "Animation");
    } else if (tab !== "all") {
      filtered = movies.filter((m) => m.media_type === tab);
    }
    if (filtered.length > 0) {
      filteredCategories[cat] = filtered;
    }
  });

  let topSectionTitle = "Top Trending Now";
  let topSectionItems = filteredTrending;
  
  if (topSectionItems.length < 6 && Object.values(filteredCategories).length > 0) {
    // Fallback if TMDB trending returns too few items for this specific tab (e.g., Anime)
    const extraItems = Object.values(filteredCategories).flat();
    const existingIds = new Set(topSectionItems.map(m => m.id));
    const uniqueExtras = extraItems.filter(m => {
      if (existingIds.has(m.id)) return false;
      existingIds.add(m.id);
      return true;
    });
    topSectionItems = [...topSectionItems, ...uniqueExtras].slice(0, 15);
  }

  let carouselItems = topSectionItems.length > 0 ? topSectionItems : filteredTrending;
  if (carouselItems.length === 0 && Object.values(filteredCategories).length > 0) {
    carouselItems = Object.values(filteredCategories).flat().slice(0, 5);
  }

  const hasContent = topSectionItems.length > 0 || Object.keys(filteredCategories).length > 0;

  return (
    <main className="min-h-screen bg-dark-900 selection:bg-accent selection:text-white pb-20">
      
      <HeroCarousel items={carouselItems} />

      <div className="px-6 md:px-12 -mt-12 relative z-20 space-y-12">
        
        {loading ? (
          <div className="scroll-row">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="w-[200px] h-[300px] rounded-md bg-dark-800 animate-pulse flex-shrink-0" />
            ))}
          </div>
        ) : hasContent ? (
          <>
            {topSectionItems.length > 0 && (
              <section>
                <h2 className="text-2xl font-bold text-white mb-4 px-2 font-outfit">{topSectionTitle}</h2>
                <div className="scroll-row">
                  {topSectionItems.map((m, i) => (
                    <MovieCard key={`${m.id}-top`} movie={m} index={i} />
                  ))}
                </div>
              </section>
            )}

            {Object.entries(filteredCategories).map(([cat, movies]) => (
              <section key={cat}>
                <h2 className="text-2xl font-bold text-white mb-4 px-2 font-outfit">{cat}</h2>
                <div className="scroll-row">
                  {movies.map((m, i) => (
                    <MovieCard key={`${m.id}-${cat.replace(/\s+/g, '-')}`} movie={m} index={i} />
                  ))}
                </div>
              </section>
            ))}
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

export default function HomePage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-dark-900 animate-pulse" />}>
      <HomeContent />
    </Suspense>
  );
}
