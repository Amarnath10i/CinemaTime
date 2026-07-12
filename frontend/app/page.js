"use client";
import { useState, useEffect, Suspense, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { MovieCard } from "../components/MovieCard";

/* ── Hero Carousel ─────────────────────────────── */
function HeroCarousel({ items }) {
  const [current, setCurrent] = useState(0);
  const [activeDetails, setActiveDetails] = useState(null);
  const [showTrailer, setShowTrailer] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const iframeRef = useRef(null);

  const toggleMute = () => {
    if (iframeRef.current && iframeRef.current.contentWindow) {
      const action = isMuted ? 'unMute' : 'mute';
      iframeRef.current.contentWindow.postMessage(`{"event":"command","func":"${action}","args":""}`, '*');
      setIsMuted(!isMuted);
    }
  };

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
            <div className={`absolute inset-0 w-full h-full overflow-hidden transition-opacity duration-1000 ${showTrailer ? 'opacity-100' : 'opacity-0'}`}>
              <iframe
                ref={iframeRef}
                src={`https://www.youtube.com/embed/${trailer.key}?autoplay=1&mute=1&controls=0&showinfo=0&rel=0&loop=1&playlist=${trailer.key}&enablejsapi=1&origin=${typeof window !== 'undefined' ? window.location.origin : ''}`}
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
          
          {showTrailer && trailer && (
            <button 
              onClick={toggleMute}
              className="absolute bottom-12 right-6 md:right-12 z-50 p-3 rounded-full border border-white/30 bg-black/40 hover:bg-black/60 backdrop-blur transition-all text-white pointer-events-auto"
              aria-label={isMuted ? "Unmute" : "Mute"}
            >
              {isMuted ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>
              )}
            </button>
          )}
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
            // If anime, fetch a huge pool (200) because we will aggressively filter out non-animations locally
            const fetchLimit = tab === "anime" ? 200 : 40;
            const typeQuery = (tab !== "all" && tab !== "anime") ? `&media_type=${tab}` : "";
            const res = await fetch(`/api/movies/category/${encodeURIComponent(cat)}?n=${fetchLimit}${typeQuery}`);
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
    
    // Cap the row length at 20 items and only show if it has at least 4 items
    filtered = filtered.slice(0, 20);
    if (filtered.length >= 4) {
      filteredCategories[cat] = filtered;
    }
  });

  let topSectionTitle = "Top Trending Now";
  let topSectionItems = filteredTrending;
  
  // If the Top Trending row isn't completely full (less than 15 items), fill the rest from the popular categories below
  if (topSectionItems.length < 15 && Object.values(filteredCategories).length > 0) {
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
              <div key={i} className="w-[140px] md:w-[200px] h-[210px] md:h-[300px] rounded-md bg-dark-800 relative overflow-hidden flex-shrink-0">
                <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/5 to-transparent" />
              </div>
            ))}
          </div>
        ) : hasContent ? (
          <>
            {topSectionItems.length > 0 && (
              <section>
                <div className="flex items-center gap-4 mb-4 px-2">
                  <h2 className="text-2xl font-bold text-white font-outfit">{topSectionTitle}</h2>
                  <Link href={`/category/Trending?tab=${tab}`} className="text-sm font-bold text-gray-400 hover:text-white transition-colors">
                    See All
                  </Link>
                </div>
                <div className="scroll-row">
                  {topSectionItems.map((m, i) => (
                    <MovieCard key={`${m.id}-top`} movie={m} index={i} />
                  ))}
                </div>
              </section>
            )}

            {Object.entries(filteredCategories).map(([cat, movies]) => (
              <section key={cat}>
                <div className="flex items-center gap-4 mb-4 px-2">
                  <h2 className="text-2xl font-bold text-white font-outfit">{cat}</h2>
                  <Link href={`/category/${encodeURIComponent(cat)}?tab=${tab}`} className="text-sm font-bold text-gray-400 hover:text-white transition-colors">
                    See All
                  </Link>
                </div>
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
