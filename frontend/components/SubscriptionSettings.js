"use client";
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSubscriptions } from "../context/SubscriptionContext";

export function SubscriptionSettings() {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const dropdownRef = useRef(null);
  const { platforms, isSubscribed, toggleSubscription, getSubscribedProviders } = useSubscriptions();

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const filteredPlatforms = platforms.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  const subscribedCount = getSubscribedProviders().length;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-accent/50 transition-all group"
        aria-label="Manage Subscriptions"
      >
        <div className="relative">
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {subscribedCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-accent text-black text-[10px] font-bold rounded-full flex items-center justify-center">
              {subscribedCount}
            </span>
          )}
        </div>
        <span className="text-sm font-medium text-gray-300 hidden sm:block">My Platforms</span>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="absolute right-0 top-full mt-2 w-80 md:w-96 glass rounded-2xl border border-white/10 shadow-2xl overflow-hidden z-50"
          >
            {/* Header */}
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <h4 className="font-bold text-white flex items-center gap-2">
                <svg className="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                My Subscriptions
              </h4>
              <span className="text-xs text-gray-400 bg-white/5 px-2 py-1 rounded">
                {subscribedCount} selected
              </span>
            </div>

            {/* Search */}
            <div className="p-4 border-b border-white/10">
              <input
                type="text"
                placeholder="Search platforms..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-accent/50 focus:bg-white/10 text-sm"
              />
            </div>

            {/* Platform List */}
            <div className="max-h-[400px] overflow-y-auto p-2">
              {filteredPlatforms.map((platform) => {
                const subscribed = isSubscribed(platform.id);
                return (
                  <motion.button
                    key={platform.id}
                    onClick={() => toggleSubscription(platform.id)}
                    whileTap={{ scale: 0.98 }}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${
                      subscribed
                        ? "bg-accent/10 border border-accent/30"
                        : "hover:bg-white/5 hover:border-white/10 border border-transparent"
                    }`}
                  >
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-white text-sm flex-shrink-0"
                      style={{ backgroundColor: platform.color }}
                    >
                      {platform.icon}
                    </div>
                    <div className="flex-1 text-left min-w-0">
                      <p className="font-medium text-white truncate">{platform.name}</p>
                      <p className="text-xs text-gray-400">India</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {subscribed && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-accent/20 text-accent border border-accent/30">
                          Active
                        </span>
                      )}
                      <div
                        className={`relative w-10 h-6 rounded-full transition-colors ${
                          subscribed ? "bg-accent" : "bg-white/10"
                        }`}
                      >
                        <div
                          className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-md transition-transform ${
                            subscribed ? "translate-x-5" : "translate-x-0.5"
                          }`}
                        />
                      </div>
                    </div>
                  </motion.button>
                );
              })}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-white/10">
              <p className="text-xs text-gray-500 text-center mb-3">
                Toggle platforms you subscribe to. Only these will show in "Where to Watch".
              </p>
              <button
                onClick={() => setIsOpen(false)}
                className="w-full py-2 px-4 bg-white/5 border border-white/10 rounded-lg text-gray-300 hover:text-white hover:bg-white/10 transition-colors text-sm font-medium"
              >
                Done
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}