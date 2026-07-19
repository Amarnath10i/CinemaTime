"use client";
import { useState, useEffect, Suspense } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { MovieCard } from "../../components/MovieCard";

function VibesContent() {
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedVibe, setSelectedVibe] = useState(null);
  const [vibeMovies, setVibeMovies] = useState([]);
  const [loadingMovies, setLoadingMovies] = useState(false);

  useEffect(() => {
    fetch("/api/vibes")
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setClusters(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleSelectVibe = async (cluster) => {
    if (selectedVibe?.id === cluster.id) {
      setSelectedVibe(null);
      setVibeMovies([]);
      return;
    }
    
    setSelectedVibe(cluster);
    setLoadingMovies(true);
    setVibeMovies([]);
    
    try {
      const res = await fetch(`/api/vibes/${cluster.id}`);
      const data = await res.json();
      setVibeMovies(Array.isArray(data) ? data : []);
    } catch (e) {
      setVibeMovies([]);
    } finally {
      setLoadingMovies(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-900">
        <div className="w-16 h-16 border-[3px] border-dark-700 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (clusters.length === 0) {
    return (
      <div className="min-h-screen pt-32 px-6 flex flex-col items-center text-center">
        <h1 className="text-5xl font-black font-outfit uppercase tracking-tighter mb-6 text-white drop-shadow-md">
          Discover <span className="text-[#00b4ff]">Vibes</span>
        </h1>
        <p className="text-gray-400 max-w-xl text-lg mb-8">
          Vibes are not generated yet. Please run the dataset builder in your terminal to pre-compute mood clusters.
        </p>
        <code className="block bg-black/50 text-[#00b4ff] p-4 rounded-lg font-mono text-sm shadow-inner text-left">
          cd backend<br/>
          python build_dataset.py
        </code>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-dark-900 pb-20 pt-28 px-6 md:px-12">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h1 className="text-5xl md:text-7xl font-black font-outfit uppercase tracking-tighter mb-4 text-white drop-shadow-md">
            Discover <span className="text-[#00b4ff]">Vibes</span>
          </h1>
          <p className="text-gray-400 max-w-2xl mx-auto text-lg md:text-xl">
            Explore movies by mood, theme, and feeling. Powered by AI semantic clustering.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 mb-16">
          {clusters.map((c, i) => (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => handleSelectVibe(c)}
              className={`glass rounded-2xl p-6 cursor-pointer group transition-all duration-300 relative overflow-hidden ${
                selectedVibe?.id === c.id 
                  ? "ring-2 ring-[#00b4ff] shadow-[0_0_30px_rgba(0,180,255,0.3)] bg-white/10" 
                  : "hover:bg-white/5 hover:-translate-y-1 hover:shadow-xl"
              }`}
            >
              <div className="absolute -right-12 -top-12 text-9xl opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 group-hover:rotate-12 duration-500">
                {c.name.split(" ")[0]}
              </div>
              
              <h3 className="text-xl font-bold text-white mb-2 font-outfit tracking-wide">{c.name}</h3>
              <p className="text-xs text-gray-400 mb-6 font-medium leading-relaxed">{c.description}</p>
              
              <div className="flex -space-x-4">
                {c.samples?.map((s, idx) => (
                  <div key={idx} className="w-12 h-16 rounded-md overflow-hidden border border-white/20 shadow-md">
                    {s.poster ? (
                      <img src={s.poster} alt={s.title} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full bg-dark-700" />
                    )}
                  </div>
                ))}
              </div>
              <div className="mt-4 text-[10px] font-bold uppercase tracking-widest text-gray-500">
                {c.size} titles
              </div>
            </motion.div>
          ))}
        </div>

        {selectedVibe && (
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass rounded-2xl p-8"
          >
            <div className="flex items-end justify-between mb-8">
              <div>
                <h2 className="text-3xl font-black text-white font-outfit uppercase tracking-wider">
                  {selectedVibe.name}
                </h2>
                <p className="text-gray-400 mt-2">{selectedVibe.description}</p>
              </div>
            </div>
            
            {loadingMovies ? (
              <div className="scroll-row">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="w-[140px] md:w-[200px] h-[210px] md:h-[300px] rounded-md bg-dark-800 relative overflow-hidden flex-shrink-0 animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="scroll-row">
                {vibeMovies.map((m, i) => (
                  <MovieCard key={`${m.id}-${m.media_type}`} movie={m} index={i} />
                ))}
              </div>
            )}
          </motion.div>
        )}
      </div>
    </main>
  );
}

export default function VibesPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-dark-900">
        <div className="w-16 h-16 border-[3px] border-dark-700 border-t-accent rounded-full animate-spin" />
      </div>
    }>
      <VibesContent />
    </Suspense>
  );
}
