"use client";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";

export function AIAssistant() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [replyText, setReplyText] = useState("");
  const inputRef = useRef(null);
  const wrapperRef = useRef(null);
  const router = useRouter();

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setIsExpanded(false);
        setResults([]);
        setReplyText("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Auto-focus input when expanded
  useEffect(() => {
    if (isExpanded) setTimeout(() => inputRef.current?.focus(), 100);
  }, [isExpanded]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setResults([]);
    setReplyText("");

    try {
      const res = await fetch("/api/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query }),
      });
      const data = await res.json();
      setReplyText(data.reply || "");
      setResults(data.movies || []);
    } catch {
      setReplyText("Could not reach the server.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (movie) => {
    setIsExpanded(false);
    setQuery("");
    setResults([]);
    setReplyText("");
    router.push(`/movie/${movie.id}?type=${movie.media_type || "movie"}`);
  };

  const handleIconClick = () => {
    setIsExpanded(true);
  };

  return (
    <div className="relative flex items-center h-[40px]" ref={wrapperRef}>
      {/* Inline expanding search bar */}
      <div
        className={`flex items-center h-full transition-all duration-300 ${
          isExpanded
            ? "bg-black/50 backdrop-blur-md border border-white/15 rounded-full px-4"
            : "bg-transparent border border-transparent"
        }`}
      >
        {/* Search Icon Button */}
        <button
          onClick={handleIconClick}
          className={`flex items-center justify-center rounded-full transition-colors ${
            isExpanded ? "text-gray-400" : "p-2 hover:bg-white/10 text-white"
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </button>

        {/* Input field - expands inline */}
        <form onSubmit={handleSearch} className="flex items-center">
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search movies, actors..."
            className={`bg-transparent text-sm text-white placeholder-gray-500 focus:outline-none transition-all duration-300 overflow-hidden ${
              isExpanded ? "w-36 md:w-56 lg:w-72 ml-3 opacity-100" : "w-0 opacity-0 ml-0 border-none p-0"
            }`}
          />
        </form>
      </div>

      {/* Results Dropdown */}
      <AnimatePresence>
        {isExpanded && (query.length >= 2 || results.length > 0 || loading) && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.15 }}
            className="absolute top-12 right-0 w-[300px] md:w-[400px] bg-black/80 backdrop-blur-xl border border-white/10 shadow-2xl rounded-lg overflow-hidden z-[200]"
          >
            <div className="max-h-[60vh] overflow-y-auto">
              {loading && (
                <div className="flex items-center justify-center py-6 gap-2">
                  <div className="w-1.5 h-1.5 bg-[#00b4ff] rounded-full animate-bounce" />
                  <div className="w-1.5 h-1.5 bg-[#00b4ff] rounded-full animate-bounce" style={{ animationDelay: "75ms" }} />
                  <div className="w-1.5 h-1.5 bg-[#00b4ff] rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                </div>
              )}

              {!loading && replyText && results.length === 0 && (
                <div className="px-4 py-4 text-sm text-gray-400 text-center">{replyText}</div>
              )}

              {!loading && results.length > 0 && (
                <>
                  {results.map((m) => (
                    <div
                      key={`${m.id}-${m.media_type}`}
                      onClick={() => handleSelect(m)}
                      className="flex items-center gap-3 px-4 py-3 hover:bg-white/10 cursor-pointer transition-colors border-b border-white/5 last:border-b-0"
                    >
                      <img
                        src={m.poster}
                        alt={m.title}
                        className="w-9 h-13 rounded object-cover bg-dark-700 flex-shrink-0"
                        onError={(e) => { e.target.src = "https://via.placeholder.com/36x50?text=?"; }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-200 truncate">{m.title}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-[#00b4ff] border border-[#00b4ff]/30 px-1.5 py-0.5 rounded">
                            {m.media_type || "movie"}
                          </span>
                          {m.rating > 0 && (
                            <span className="text-[11px] text-yellow-400">★ {Number(m.rating).toFixed(1)}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
