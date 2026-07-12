"use client";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";

export function AIAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [replyText, setReplyText] = useState("");
  const inputRef = useRef(null);
  const panelRef = useRef(null);
  const router = useRouter();

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e) {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Auto-focus input when opened
  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 150);
  }, [isOpen]);

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
    setIsOpen(false);
    setQuery("");
    setResults([]);
    setReplyText("");
    router.push(`/movie/${movie.id}?type=${movie.media_type || "movie"}`);
  };

  return (
    <div className="relative" ref={panelRef}>
      {/* Atom Icon Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative w-10 h-10 flex items-center justify-center group"
        aria-label="AI Search Assistant"
      >
        {/* Animated Atom SVG */}
        <svg
          width="28"
          height="28"
          viewBox="0 0 100 100"
          className="transition-transform duration-300 group-hover:scale-110"
        >
          {/* Orbit 1 */}
          <ellipse
            cx="50" cy="50" rx="40" ry="14"
            fill="none"
            stroke="url(#atomGrad1)"
            strokeWidth="2"
            className="animate-[atomSpin1_3s_linear_infinite]"
          />
          {/* Orbit 2 */}
          <ellipse
            cx="50" cy="50" rx="40" ry="14"
            fill="none"
            stroke="url(#atomGrad2)"
            strokeWidth="2"
            transform="rotate(60 50 50)"
            className="animate-[atomSpin2_4s_linear_infinite]"
          />
          {/* Orbit 3 */}
          <ellipse
            cx="50" cy="50" rx="40" ry="14"
            fill="none"
            stroke="url(#atomGrad3)"
            strokeWidth="2"
            transform="rotate(120 50 50)"
            className="animate-[atomSpin3_5s_linear_infinite]"
          />
          {/* Core */}
          <circle cx="50" cy="50" r="6" fill="url(#coreGrad)">
            <animate attributeName="r" values="5;7;5" dur="2s" repeatCount="indefinite" />
          </circle>
          {/* Glow */}
          <circle cx="50" cy="50" r="10" fill="url(#coreGrad)" opacity="0.2">
            <animate attributeName="r" values="8;14;8" dur="2s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.3;0.1;0.3" dur="2s" repeatCount="indefinite" />
          </circle>

          <defs>
            <linearGradient id="atomGrad1" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#00b4ff" stopOpacity="0.2" />
              <stop offset="50%" stopColor="#00b4ff" stopOpacity="1" />
              <stop offset="100%" stopColor="#a855f7" stopOpacity="0.2" />
            </linearGradient>
            <linearGradient id="atomGrad2" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#a855f7" stopOpacity="0.2" />
              <stop offset="50%" stopColor="#a855f7" stopOpacity="1" />
              <stop offset="100%" stopColor="#00b4ff" stopOpacity="0.2" />
            </linearGradient>
            <linearGradient id="atomGrad3" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#00b4ff" stopOpacity="0.2" />
              <stop offset="50%" stopColor="#ec4899" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#a855f7" stopOpacity="0.2" />
            </linearGradient>
            <radialGradient id="coreGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="50%" stopColor="#00b4ff" />
              <stop offset="100%" stopColor="#a855f7" />
            </radialGradient>
          </defs>
        </svg>
      </button>

      {/* Search Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="absolute top-14 right-0 w-[90vw] md:w-[420px] bg-dark-800/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl z-[200] overflow-hidden"
          >
            {/* Search Input */}
            <form onSubmit={handleSearch} className="p-4 border-b border-white/5">
              <div className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-full px-4 py-2 focus-within:border-[#00b4ff]/50 transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400 flex-shrink-0">
                  <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search movies, actors, directors..."
                  className="flex-1 bg-transparent text-sm text-white placeholder-gray-400 focus:outline-none"
                />
                {query.trim() && (
                  <button
                    type="submit"
                    disabled={loading}
                    className="text-[#00b4ff] hover:text-white transition-colors disabled:opacity-40"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                      <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                  </button>
                )}
              </div>
            </form>

            {/* Results Area */}
            <div className="max-h-[60vh] overflow-y-auto">
              {loading && (
                <div className="flex items-center justify-center py-8 gap-2">
                  <div className="w-1.5 h-1.5 bg-[#00b4ff] rounded-full animate-bounce" />
                  <div className="w-1.5 h-1.5 bg-[#00b4ff] rounded-full animate-bounce" style={{ animationDelay: "75ms" }} />
                  <div className="w-1.5 h-1.5 bg-[#00b4ff] rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                </div>
              )}

              {!loading && replyText && results.length === 0 && (
                <div className="px-4 py-6 text-center text-gray-400 text-sm">{replyText}</div>
              )}

              {!loading && results.length > 0 && (
                <>
                  {replyText && (
                    <div className="px-4 pt-3 pb-1 text-xs font-medium text-gray-400 uppercase tracking-wider">{replyText}</div>
                  )}
                  {results.map((m) => (
                    <div
                      key={`${m.id}-${m.media_type}`}
                      onClick={() => handleSelect(m)}
                      className="flex items-center gap-3 px-4 py-3 hover:bg-white/5 cursor-pointer transition-colors border-b border-white/5 last:border-b-0"
                    >
                      {/* Poster Thumbnail */}
                      <img
                        src={m.poster}
                        alt={m.title}
                        className="w-10 h-14 rounded object-cover bg-dark-700 flex-shrink-0"
                        onError={(e) => { e.target.src = "https://via.placeholder.com/40x56?text=?"; }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate">{m.title}</p>
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

              {/* Empty state - before any search */}
              {!loading && !replyText && results.length === 0 && (
                <div className="px-4 py-8 text-center">
                  <p className="text-gray-500 text-sm">Try searching for a movie, actor, or director</p>
                  <div className="flex flex-wrap justify-center gap-2 mt-3">
                    {["Tom Cruise", "Inception", "Anime", "Christopher Nolan"].map((hint) => (
                      <button
                        key={hint}
                        onClick={() => { setQuery(hint); }}
                        className="text-xs bg-white/5 border border-white/10 px-3 py-1.5 rounded-full text-gray-300 hover:bg-white/10 hover:text-white transition-colors"
                      >
                        {hint}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
