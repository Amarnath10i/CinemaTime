"use client";
import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { MovieCard } from "../../components/MovieCard";
import Link from "next/link";

const USER_COLORS = ["#00b4ff", "#ff0066", "#00ff66", "#ffcc00", "#9933ff"];

export default function GroupWatchPage() {
  const [users, setUsers] = useState([
    { id: 1, name: "User 1", color: USER_COLORS[0], movies: [], selectedIds: new Set() },
    { id: 2, name: "User 2", color: USER_COLORS[1], movies: [], selectedIds: new Set() }
  ]);
  
  const [activeUserId, setActiveUserId] = useState(1);
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (query.length < 2) { setSuggestions([]); return; }
    const timer = setTimeout(async () => {
      try {
        setIsSearching(true);
        const res = await fetch(`/api/movies/titles?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setSuggestions(data);
      } catch (e) {
        setSuggestions([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const addUser = () => {
    if (users.length >= 5) return;
    const newId = Math.max(...users.map(u => u.id)) + 1;
    setUsers([...users, {
      id: newId,
      name: `User ${users.length + 1}`,
      color: USER_COLORS[users.length],
      movies: [],
      selectedIds: new Set()
    }]);
    setActiveUserId(newId);
  };

  const removeUser = (id) => {
    if (users.length <= 2) return;
    const newUsers = users.filter(u => u.id !== id);
    setUsers(newUsers);
    if (activeUserId === id) setActiveUserId(newUsers[0].id);
  };

  const selectMovie = (movie) => {
    setUsers(users.map(u => {
      if (u.id === activeUserId && !u.selectedIds.has(movie.id)) {
        const newSet = new Set(u.selectedIds);
        newSet.add(movie.id);
        return { ...u, movies: [...u.movies, movie], selectedIds: newSet };
      }
      return u;
    }));
    setQuery("");
    setSuggestions([]);
  };

  const removeMovie = (userId, movieId) => {
    setUsers(users.map(u => {
      if (u.id === userId) {
        const newSet = new Set(u.selectedIds);
        newSet.delete(movieId);
        return { ...u, movies: u.movies.filter(m => m.id !== movieId), selectedIds: newSet };
      }
      return u;
    }));
  };

  const activeUser = users.find(u => u.id === activeUserId);
  const totalMovies = users.reduce((sum, u) => sum + u.movies.length, 0);

  const getRecommendations = async () => {
    if (totalMovies === 0) return;
    setLoading(true);
    setRecommendations([]);
    
    try {
      const userLists = users.map(u => u.movies.map(m => m.id));
      const res = await fetch("/api/group-recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ users: userLists, n: 15, diversity: 0.5 })
      });
      const data = await res.json();
      setRecommendations(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-dark-900 pb-20 pt-28 px-6 md:px-12">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-6xl font-black font-outfit uppercase tracking-tighter mb-4 text-white drop-shadow-md">
            Group <span className="text-[#00b4ff]">Watch</span>
          </h1>
          <p className="text-gray-400 max-w-2xl mx-auto text-lg">
            Find the perfect movie for everyone. Add up to 5 people, pick some favorites, and let AI find the consensus.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Users & Inputs */}
          <div className="lg:col-span-1 space-y-6">
            <div className="glass rounded-2xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold font-outfit">Who's watching?</h2>
                {users.length < 5 && (
                  <button onClick={addUser} className="text-xs font-bold uppercase tracking-wider text-accent hover:text-white transition-colors">
                    + Add Person
                  </button>
                )}
              </div>
              
              <div className="space-y-3">
                {users.map((u) => (
                  <div 
                    key={u.id}
                    onClick={() => setActiveUserId(u.id)}
                    className={`p-3 rounded-lg flex items-center justify-between cursor-pointer transition-all ${
                      activeUserId === u.id ? "bg-white/10 ring-1 ring-white/30" : "bg-black/30 hover:bg-black/50"
                    }`}
                    style={{ borderLeft: `4px solid ${u.color}` }}
                  >
                    <div>
                      <div className="font-bold text-sm text-white">{u.name}</div>
                      <div className="text-xs text-gray-500">{u.movies.length} movies selected</div>
                    </div>
                    {users.length > 2 && (
                      <button 
                        onClick={(e) => { e.stopPropagation(); removeUser(u.id); }}
                        className="text-gray-500 hover:text-red-400"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="glass rounded-2xl p-6 relative">
              <h2 className="text-lg font-bold font-outfit mb-2">
                Add movies for <span style={{color: activeUser.color}}>{activeUser.name}</span>
              </h2>
              
              <div className="relative">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search a movie..."
                  className="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-3 text-sm text-white focus:outline-none focus:border-[#00b4ff] transition-colors"
                />
                
                {query.length >= 2 && (
                  <div className="absolute top-full left-0 right-0 mt-2 bg-dark-800 border border-white/10 rounded-lg shadow-2xl max-h-60 overflow-y-auto z-50">
                    {suggestions.map(s => (
                      <div 
                        key={s.id}
                        onClick={() => selectMovie(s)}
                        className="px-4 py-2 hover:bg-white/10 cursor-pointer text-sm border-b border-white/5 last:border-0 flex justify-between items-center"
                      >
                        <span className="line-clamp-1">{s.title}</span>
                        {activeUser.selectedIds.has(s.id) && <span className="text-xs text-[#00b4ff]">Added</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="mt-6 space-y-2 max-h-60 overflow-y-auto">
                {activeUser.movies.map(m => (
                  <div key={m.id} className="flex items-center justify-between bg-black/30 px-3 py-2 rounded text-sm">
                    <span className="line-clamp-1">{m.title}</span>
                    <button onClick={() => removeMovie(activeUser.id, m.id)} className="text-gray-500 hover:text-white ml-2">✕</button>
                  </div>
                ))}
                {activeUser.movies.length === 0 && (
                  <div className="text-center text-sm text-gray-500 py-4">No movies added yet.</div>
                )}
              </div>
            </div>
            
            <button
              onClick={getRecommendations}
              disabled={totalMovies === 0 || loading}
              className={`w-full py-4 rounded-xl font-bold font-outfit text-lg tracking-wider transition-all shadow-lg ${
                totalMovies > 0 
                  ? "bg-[#00b4ff] hover:bg-[#0090cc] text-black hover:scale-[1.02] cursor-pointer" 
                  : "bg-white/5 text-gray-500 cursor-not-allowed"
              }`}
            >
              {loading ? "Finding Consensus..." : "Find Movies for Everyone"}
            </button>
          </div>

          {/* Right Column: Results */}
          <div className="lg:col-span-2">
            {recommendations.length > 0 ? (
              <div className="glass rounded-2xl p-6 min-h-full">
                <h2 className="text-2xl font-black font-outfit uppercase tracking-widest mb-6">Consensus Picks</h2>
                
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {recommendations.map((m, i) => (
                    <motion.div 
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.1 }}
                      key={m.id}
                      className="relative group"
                    >
                      <MovieCard movie={m} index={i} />
                      
                      {/* Compatibility Bar */}
                      {m.user_scores && (
                        <div className="absolute -bottom-2 left-2 right-2 h-1.5 bg-black/80 rounded-full flex overflow-hidden shadow-lg z-10 border border-white/10">
                          {m.user_scores.map((score, ui) => (
                            <div 
                              key={ui} 
                              style={{ 
                                width: `${100 / users.length}%`, 
                                backgroundColor: users[ui]?.color || '#fff',
                                opacity: score > 50 ? 1 : 0.3
                              }} 
                              title={`${users[ui]?.name}: ${score}% match`}
                            />
                          ))}
                        </div>
                      )}
                    </motion.div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="glass rounded-2xl p-6 h-full flex flex-col items-center justify-center text-center opacity-50 min-h-[400px]">
                <div className="text-6xl mb-4">🍿</div>
                <h3 className="text-xl font-bold font-outfit mb-2">Waiting for input</h3>
                <p className="text-gray-400 text-sm max-w-sm">
                  Add movies for at least one person and click "Find Movies for Everyone" to see AI recommendations.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
