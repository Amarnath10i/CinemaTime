"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

export function SearchModal() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const router = useRouter();
  const searchRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (query.length < 2) { setSuggestions([]); return; }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/movies/titles?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setSuggestions(data);
        setIsOpen(true);
      } catch (_) { setSuggestions([]); }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Close dropdown and collapse bar when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setIsOpen(false);
        if (query.length === 0) {
          setIsExpanded(false);
        }
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [query]);

  const handleSelect = (s) => {
    setIsOpen(false);
    setQuery("");
    setIsExpanded(false);
    router.push(`/movie/${s.id}?type=${s.media_type}`);
  };

  const handleIconClick = () => {
    setIsExpanded(true);
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  return (
    <div className="relative flex items-center h-[40px]" ref={searchRef}>
      <div 
        className={`flex items-center h-full transition-all duration-300 ${
          isExpanded 
            ? "bg-white/10 border border-white/20 rounded-full px-3 focus-within:bg-white/20 focus-within:border-[#00b4ff]" 
            : "bg-transparent border border-transparent"
        }`}
      >
        <button 
          onClick={handleIconClick}
          className={`flex items-center justify-center rounded-full transition-colors ${
            isExpanded ? "text-gray-400" : "p-2 hover:bg-white/10 text-white"
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </button>

        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (e.target.value.length >= 2) setIsOpen(true);
          }}
          onFocus={() => { if (query.length >= 2) setIsOpen(true); }}
          placeholder="Search movies..."
          className={`bg-transparent text-sm text-white placeholder-gray-400 focus:outline-none transition-all duration-300 overflow-hidden ${
            isExpanded ? "w-32 md:w-48 lg:w-64 ml-3 opacity-100" : "w-0 opacity-0 ml-0 border-none p-0"
          }`}
        />
      </div>

      {isOpen && (query.length >= 2) && (
        <div className="absolute top-12 right-0 w-[300px] md:w-[400px] bg-dark-800 border border-white/10 shadow-2xl rounded-lg overflow-hidden z-[200]">
          <div className="max-h-[60vh] overflow-y-auto scroll-row flex-col pb-0 pt-0">
            {suggestions.map((s) => (
              <div
                key={`${s.id}-${s.media_type}`}
                onClick={() => handleSelect(s)}
                className="px-4 py-3 hover:bg-white/10 cursor-pointer transition-colors flex items-center justify-between border-b border-white/5 last:border-b-0"
              >
                <span className="text-sm font-medium text-gray-200 line-clamp-1 mr-4">{s.title}</span>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#00b4ff] border border-[#00b4ff]/30 px-2 py-0.5 rounded flex-shrink-0">
                  {s.media_type || "Movie"}
                </span>
              </div>
            ))}
            {suggestions.length === 0 && (
              <div className="px-4 py-4 text-sm text-gray-500 text-center">No results found for "{query}"</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
