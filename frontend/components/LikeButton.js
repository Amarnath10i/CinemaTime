"use client";
import { useLikes } from "./likes";

export function LikeButton({ movie, className = "" }) {
  const { isLiked, toggle } = useLikes();
  const liked = isLiked(movie.id);

  return (
    <button
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        toggle(movie);
      }}
      aria-pressed={liked}
      aria-label={liked ? `Remove ${movie.title} from liked movies` : `Like ${movie.title}`}
      className={`flex items-center gap-2 px-6 py-3 rounded font-bold text-lg border transition-colors ${
        liked
          ? "bg-[#ff0066]/20 border-[#ff0066]/60 text-white hover:bg-[#ff0066]/30"
          : "bg-white/10 border-white/20 text-white hover:bg-white/20"
      } ${className}`}
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
        fill={liked ? "#ff0066" : "none"} stroke={liked ? "#ff0066" : "currentColor"}
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
      </svg>
      {liked ? "Liked" : "Like"}
    </button>
  );
}
