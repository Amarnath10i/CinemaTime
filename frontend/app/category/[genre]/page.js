"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { MovieCard } from "../../../components/MovieCard";
import { EmptyState } from "../../../components/EmptyState";

export default function CategoryPage({ params }) {
  const { genre } = params;
  const decodedGenre = decodeURIComponent(genre);
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") || "all";
  
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [serverDown, setServerDown] = useState(false);

  useEffect(() => {
    const fetchMovies = async () => {
      setLoading(true);
      setServerDown(false);
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
        if (!res.ok) throw new Error(`${res.status} from ${url}`);
        const data = await res.json();
        
        if (Array.isArray(data)) {
          let filtered = data;
          if (tab === "anime") {
            filtered = data.filter(m => {
              const genres = (m.genres || "").toLowerCase();
              if (m.media_type === "anime") return true;
              // Trending items carry original_language; catalogue items don't.
              return genres.includes("animation") && (!m.original_language || m.original_language === "ja");
            });
          } else if (tab !== "all") {
            filtered = data.filter(m => m.media_type === tab);
          }
          setMovies(filtered);
        }
      } catch (e) {
        console.error("Error fetching category", e);
        setServerDown(true);
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
          <EmptyState serverDown={serverDown} label={(tab === "tv" ? "TV shows" : tab === "anime" ? "anime" : tab === "movie" ? "movies" : "titles") + " in " + decodedGenre} />
        )}
      </div>
    </main>
  );
}
