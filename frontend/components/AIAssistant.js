"use client";
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MovieCard } from "./MovieCard";

export function AIAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Hi! I'm your Cinema AI. Ask me for movies by a specific actor, director, or genre!" }
  ]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMessage = { role: "user", text: query };
    setMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setLoading(true);

    try {
      const res = await fetch("/api/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage.text })
      });
      const data = await res.json();
      
      setMessages((prev) => [...prev, { 
        role: "assistant", 
        text: data.reply || "Here is what I found:", 
        movies: data.movies || [] 
      }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", text: "Sorry, my servers are currently unreachable." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-[100] w-14 h-14 rounded-full bg-black/60 backdrop-blur-md border border-white/10 shadow-lg flex items-center justify-center hover:bg-black/80 hover:scale-110 transition-all group overflow-hidden"
        style={{
          borderTopRightRadius: "4px", // gives a slight teardrop/drop shape
          transform: "rotate(-45deg)",
        }}
      >
        {/* Glow effect */}
        <div className="absolute inset-0 bg-gradient-to-tr from-[#00b4ff]/20 to-purple-500/20 opacity-0 group-hover:opacity-100 transition-opacity" />
        
        <div style={{ transform: "rotate(45deg)" }}>
          {isOpen ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
              <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z"></path>
              <path d="M12 16V12"></path>
              <path d="M12 8H12.01"></path>
            </svg>
          )}
        </div>
      </button>

      {/* Chat Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-24 right-6 w-[90vw] md:w-[400px] h-[600px] max-h-[75vh] z-[90] glass rounded-2xl flex flex-col overflow-hidden shadow-2xl border border-white/10"
          >
            {/* Header */}
            <div className="p-4 border-b border-white/10 bg-black/40 backdrop-blur-md flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[#00b4ff] animate-pulse" />
                <h3 className="font-outfit font-bold tracking-wide">Cinema AI</h3>
              </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin scrollbar-thumb-white/10">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
                  <div className={`max-w-[85%] p-3 rounded-2xl ${msg.role === "user" ? "bg-[#00b4ff]/20 text-white border border-[#00b4ff]/30 rounded-br-sm" : "bg-white/5 text-gray-200 border border-white/10 rounded-bl-sm"}`}>
                    <p className="text-sm">{msg.text}</p>
                  </div>
                  
                  {/* Results Horizontal Carousel (if movies returned) */}
                  {msg.movies && msg.movies.length > 0 && (
                    <div className="w-full mt-3 flex overflow-x-auto gap-3 pb-2 snap-x scrollbar-thin scrollbar-thumb-white/10">
                      {msg.movies.map((m, i) => (
                        <div key={m.id} className="w-[100px] flex-shrink-0 snap-start">
                          <MovieCard movie={m} index={i} disableHover={true} />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              
              {loading && (
                <div className="flex items-start">
                  <div className="bg-white/5 border border-white/10 p-4 rounded-2xl rounded-bl-sm flex gap-1">
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-75" />
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-150" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="p-3 border-t border-white/10 bg-black/40 backdrop-blur-md flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask for a movie or actor..."
                className="flex-1 bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-[#00b4ff]/50 transition-colors"
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="w-10 h-10 rounded-full bg-[#00b4ff]/20 text-[#00b4ff] flex items-center justify-center hover:bg-[#00b4ff]/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
