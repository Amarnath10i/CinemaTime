"use client";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TrailerPlayer, youtubeThumb, youtubeWatchUrl, youtubeSearchUrl } from "./TrailerPlayer";

/** Fullscreen player for a title's trailers, teasers and clips, with a picker strip. */
export function TrailerModal({ open, videos = [], startIndex = 0, title = "", year = "", onClose }) {
  const [active, setActive] = useState(startIndex);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    if (open) {
      setActive(startIndex);
      setUnavailable(false);
    }
  }, [open, startIndex]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = overflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  const pick = (i) => {
    setActive(i);
    setUnavailable(false);
  };

  const current = videos[active];

  return (
    <AnimatePresence>
      {open && videos.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[9999] bg-black/95 flex flex-col"
          role="dialog"
          aria-modal="true"
          aria-label={`${title} trailer`}
        >
          <div className="flex items-center justify-between gap-4 px-4 md:px-8 py-4">
            <div className="min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500">{current?.type || "Trailer"}</p>
              <h2 className="text-white font-bold text-lg md:text-xl truncate">{current?.name || title}</h2>
            </div>
            <button
              onClick={onClose}
              aria-label="Close trailer"
              className="flex-shrink-0 p-3 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors border border-white/20"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>

          <div className="flex-1 min-h-0 flex items-center justify-center px-2 md:px-8">
            <div className="relative w-full max-w-6xl aspect-video max-h-full bg-black rounded-lg overflow-hidden shadow-2xl">
              {unavailable ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-center p-6">
                  <p className="text-gray-300 text-lg font-semibold">These videos can&apos;t be played here.</p>
                  <div className="flex flex-wrap justify-center gap-3">
                    {current && (
                      <a href={youtubeWatchUrl(current.key)} target="_blank" rel="noopener noreferrer" className="px-5 py-2.5 rounded bg-white text-black font-bold hover:bg-gray-200 transition-colors">
                        Watch on YouTube
                      </a>
                    )}
                    <a href={youtubeSearchUrl(title, year)} target="_blank" rel="noopener noreferrer" className="px-5 py-2.5 rounded bg-white/10 text-white font-bold border border-white/20 hover:bg-white/20 transition-colors">
                      Search YouTube
                    </a>
                  </div>
                </div>
              ) : (
                <TrailerPlayer
                  videos={videos}
                  startIndex={active}
                  onIndexChange={setActive}
                  onUnavailable={() => setUnavailable(true)}
                  className="absolute inset-0 w-full h-full"
                />
              )}
            </div>
          </div>

          {videos.length > 1 && (
            <div className="px-4 md:px-8 py-4">
              <div className="flex gap-3 overflow-x-auto pb-2 max-w-6xl mx-auto">
                {videos.map((v, i) => (
                  <button
                    key={v.key}
                    onClick={() => pick(i)}
                    className={`group flex-shrink-0 w-40 text-left rounded-md overflow-hidden border transition-colors ${i === active ? "border-white" : "border-white/10 hover:border-white/40"}`}
                  >
                    <div className="relative aspect-video bg-dark-800">
                      <img src={youtubeThumb(v.key)} alt="" loading="lazy" className="w-full h-full object-cover" />
                      <span className="absolute bottom-1 left-1 text-[9px] font-bold uppercase tracking-wider bg-black/80 text-white px-1.5 py-0.5 rounded">{v.type}</span>
                    </div>
                    <p className="text-[11px] text-gray-300 px-2 py-1.5 line-clamp-2 leading-tight">{v.name}</p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
