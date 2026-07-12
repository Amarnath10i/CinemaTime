"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { MovieCard } from "../../../components/MovieCard";

export default function CategoryPage({ params }) {
  const { genre } = params;
  const decodedGenre = decodeURIComponent(genre);
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") || "all";
  
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMovies = async () => {
      setLoading(true);
      try {
        let url;
        if (decodedGenre.toLowerCase() === "trending") {
          url = `/api/trending`;
        } else {
          const typeQuery = (tab !== "all" && tab !== "anime") ? `&media_type=${tab}` : "";
          const fetchLimit = tab === "anime" ? 200 : 60;
          url = `/api/movies/category/${encodeURIComponent(decodedGenre)}?n=${fetchLimit}${typeQuery}`;
        }
        
        const res = await fetch(url);
        const data = await res.json();
        
        if (Array.isArray(data)) {
          let filtered = data;
          if (tab === "anime") {
            filtered = data.filter(m => {
              const genres = (m.genres || "").toLowerCase();
              const title = (m.title || "").toLowerCase();
              return genres.includes("animation") || genres.includes("16") ||
                title.match(/anime|naruto|one piece|dragon ball|jujutsu|demon slayer|attack on titan|bleach|my hero/);
            });
          } else if (tab !== "all") {
            filtered = data.filter(m => m.media_type === tab);
          }
          setMovies(filtered);
        }
      } catch (e) {
        console.error("Error fetching category", e);
      } finally {
        setLoading(false);
      }
    };
    
    fetchMovies();
  }, [decodedGenre, tab]);

  return (
    <main className="min-h-screen bg-dark-900 pt-32 pb-20 px-6 md:px-12 selection:bg-accent selection:text-white">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl md:text-5xl font-black text-white font-outfit mb-8 capitalize">
          {decodedGenre} {tab !== "all" && <span className="text-gray-500 uppercase text-2xl tracking-widest ml-4">/ {tab}</span>}
        </h1>
        
        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
            {Array.from({ length: 18 }).map((_, i) => (
              <div key={i} className="w-full aspect-[2/3] rounded-md bg-dark-800 animate-pulse" />
            ))}
          </div>
        ) : movies.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
            {movies.map((m, i) => (
              <div key={m.id} className="w-full flex justify-center">
                <MovieCard movie={m} index={i} />
              </div>
            ))}
          </div>
        ) : (
          <div className="pt-24 text-center px-4 max-w-2xl mx-auto">
            <h3 className="text-2xl font-bold text-white mb-4">No content available for this category.</h3>
            <p className="text-gray-400 text-lg mb-8">
              It looks like your local database doesn&apos;t have any {tab === 'tv' ? 'TV Shows' : tab === 'anime' ? 'Anime' : 'items'} for {decodedGenre} yet!
            </p>
            <div className="bg-white/5 border border-white/10 rounded-xl p-6 text-left inline-block">
              <p className="text-gray-300 font-medium mb-3">To fix this, run the dataset builder in your terminal:</p>
              <code className="block bg-black/50 text-[#00b4ff] p-4 rounded-lg font-mono text-sm shadow-inner">
                cd backend<br/>
                python build_dataset.py
              </code>
              <p className="text-gray-400 text-sm mt-4">
                This will automatically fetch thousands of Movies, TV Shows, and Anime directly from TMDB and rebuild your search index!
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
