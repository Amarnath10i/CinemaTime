"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";

export function MediaBadge({ type }) {
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

export function MovieCard({ movie, index: i, priority = false }) {
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
        <div className="group relative w-full aspect-[2/3] max-w-[200px] min-w-[140px] md:min-w-[180px] lg:min-w-[200px] cursor-pointer">
          <div className="overflow-hidden rounded-md w-full h-full bg-dark-800 relative shadow-[0_4px_20px_rgba(0,0,0,0.5)] group-hover:shadow-[0_8px_30px_rgba(229,9,20,0.3)] transition-all duration-300 transform group-hover:-translate-y-2">
            
            {poster ? (
              <img
                src={poster}
                alt={movie.title}
                loading={priority ? "eager" : "lazy"}
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
                <h3 className="font-black text-white/90 text-sm md:text-lg leading-tight line-clamp-4 uppercase tracking-wider font-outfit">{movie.title}</h3>
              </div>
            )}

            <div className="absolute top-2 right-2 bg-black/80 backdrop-blur-md text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow-md border border-white/10">
              {movie.rating?.toFixed(1) || "N/A"}
            </div>
            
            <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-4">
               <MediaBadge type={movie.media_type || "movie"} />
               <p className="mt-2 text-xs md:text-sm font-bold text-white line-clamp-2 leading-tight">{movie.title}</p>
               {movie.release_date && (
                 <p className="text-[10px] md:text-xs text-gray-400 mt-1">{movie.release_date.slice(0, 4)}</p>
               )}
            </div>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
