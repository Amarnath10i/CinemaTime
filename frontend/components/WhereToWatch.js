"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSubscriptions } from "../context/SubscriptionContext";

export function WhereToWatch({ itemId, mediaType = "movie" }) {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("subscribed"); // "all" | "subscribed" | "free"
  const { isSubscribed, getSubscribedProviders } = useSubscriptions();

  useEffect(() => {
    if (!itemId) return;
    
    const fetchProviders = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/watch-providers/${itemId}`);
        const data = await res.json();
        if (data.providers) {
          setProviders(data.providers);
        }
      } catch (e) {
        console.error("Failed to fetch providers:", e);
      } finally {
        setLoading(false);
      }
    };

    fetchProviders();
  }, [itemId]);

  // Filter providers based on subscription status
  const filteredProviders = providers.filter((p) => {
    const subscribed = isSubscribed(p.provider_id);
    const isFree = p.type === "Free" || p.type === "Free with Ads";
    
    if (filter === "subscribed") return subscribed;
    if (filter === "free") return isFree;
    return true; // "all"
  });

  // Group by type
  const grouped = filteredProviders.reduce((acc, p) => {
    if (!acc[p.type]) acc[p.type] = [];
    acc[p.type].push(p);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="glass rounded-2xl p-6 animate-pulse">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded bg-white/10" />
          <div className="w-32 h-6 rounded bg-white/10" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-3 h-14 bg-white/5 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (filteredProviders.length === 0) {
    return (
      <div className="glass rounded-2xl p-6 text-center">
        <svg className="w-12 h-12 mx-auto text-gray-500 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="text-gray-400">Not available on your subscribed platforms in India</p>
        <div className="mt-3 flex justify-center gap-2">
          {["subscribed", "all", "free"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-sm rounded-full transition-colors ${
                filter === f
                  ? "bg-accent text-black font-bold"
                  : "bg-white/5 text-gray-400 hover:text-white hover:bg-white/10"
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>
    );
  }

  const openDeepLink = (provider) => {
    // Try deep link first (opens app), fallback to web
    const isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    if (isMobile) {
      // Try to open app via deep link
      window.location.href = provider.deep_link;
      // Fallback to web after 2 seconds
      setTimeout(() => {
        window.open(provider.web_url, "_blank", "noopener,noreferrer");
      }, 2000);
    } else {
      // Desktop: open web version
      window.open(provider.web_url, "_blank", "noopener,noreferrer");
    }
  };

  const typeOrder = ["Subscription", "Free with Ads", "Free", "Rent", "Buy"];
  const sortedTypes = Object.keys(grouped).sort((a, b) => 
    typeOrder.indexOf(a) - typeOrder.indexOf(b)
  );

  return (
    <div className="glass rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold font-outfit text-white flex items-center gap-2">
          <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Where to Watch
        </h3>
        <div className="flex gap-1 bg-white/5 rounded-lg p-1">
          {["subscribed", "all", "free"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-xs rounded-md transition-all ${
                filter === f
                  ? "bg-accent text-black font-bold"
                  : "text-gray-400 hover:text-white hover:bg-white/10"
              }`}
            >
              {f === "subscribed" ? "My Platforms" : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <AnimatePresence mode="popLayout">
        {sortedTypes.map((type) => (
          <motion.div
            key={type}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-6"
          >
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-accent bg-accent/10 px-2 py-0.5 rounded">
                {type}
              </span>
              <span className="text-gray-500 text-sm">{grouped[type].length} option{grouped[type].length > 1 ? "s" : ""}</span>
            </div>
            <div className="flex flex-wrap gap-3">
              {grouped[type].map((provider) => (
                <motion.button
                  key={provider.provider_id}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => openDeepLink(provider)}
                  className="flex flex-col items-center gap-2 group w-28 cursor-pointer p-3 rounded-xl bg-white/5 border border-white/10 hover:border-accent/50 hover:bg-accent/10 transition-all"
                >
                  <div className="relative w-14 h-14 rounded-lg overflow-hidden bg-white/5 flex items-center justify-center">
                    {provider.logo ? (
                      <img
                        src={`https://image.tmdb.org/t/p/w200${provider.logo}`}
                        alt={provider.name}
                        className="w-full h-full object-contain p-1 group-hover:scale-110 transition-transform"
                        onError={(e) => { e.target.style.display = "none"; e.target.nextSibling.style.display = "flex"; }}
                      />
                    ) : null}
                    <span className="text-2xl font-black text-white hidden">{provider.icon || provider.name[0]}</span>
                  </div>
                  <span className="text-xs font-semibold text-white text-center line-clamp-1 px-1">
                    {provider.name}
                  </span>
                  {isSubscribed(provider.provider_id) && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 border border-green-500/30">
                      Subscribed
                    </span>
                  )}
                </motion.button>
              ))}
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      {filter === "subscribed" && getSubscribedProviders().length === 0 && (
        <div className="text-center py-4 text-gray-500 border-t border-white/10 mt-4">
          <p className="mb-2">No platforms selected yet</p>
          <button
            onClick={() => setFilter("all")}
            className="text-accent hover:underline text-sm font-medium"
          >
            Show all available platforms →
          </button>
        </div>
      )}
    </div>
  );
}