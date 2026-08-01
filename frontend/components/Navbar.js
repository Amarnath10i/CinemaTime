"use client";
import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { AIAssistant } from "./AIAssistant";
import { SubscriptionSettings } from "./SubscriptionSettings";
import { AuthModal } from "./AuthModal";
import { useAuth } from "../context/AuthContext";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const profileRef = useRef(null);
  const { user, logout, isAuthenticated } = useAuth();

  // Close profile dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    };
    if (profileOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [profileOpen]);

  const handleLogout = () => {
    logout();
    setProfileOpen(false);
  };

  return (
    <>
      <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />

      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5 py-4 px-6 md:px-12 flex items-center justify-between transition-all duration-300">
        <Link href="/" className="flex items-center gap-1 group">
          <span className="text-3xl font-black tracking-widest uppercase font-outfit text-white group-hover:text-gray-200 transition-colors">
            CINEMA
          </span>
          <span className="text-4xl font-script text-[#00b4ff] -ml-2 mt-2 -rotate-2 group-hover:scale-105 transition-transform">
            Time
          </span>
        </Link>
        
        <div className="hidden md:flex absolute left-1/2 -translate-x-1/2 items-center gap-12 font-bold text-lg tracking-wider text-gray-300">
          <Link href="/?tab=movie" className="hover:text-white transition-colors hover:scale-105 transform">Movies</Link>
          <Link href="/?tab=tv" className="hover:text-white transition-colors hover:scale-105 transform">TV Shows</Link>
          <Link href="/vibes" className="hover:text-white transition-colors hover:scale-105 transform">Vibes</Link>
          <Link href="/group" className="hover:text-white transition-colors hover:scale-105 transform">Group Watch</Link>
        </div>

        <div className="flex items-center gap-4">
          <AIAssistant />
          <SubscriptionSettings />
          
          {isAuthenticated ? (
            <div className="relative" ref={profileRef}>
              <button
                onClick={() => setProfileOpen(!profileOpen)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-accent/50 transition-all group"
              >
                <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center font-bold text-accent text-sm">
                  {user?.name?.[0]?.toUpperCase() || "U"}
                </div>
                <span className="text-sm font-medium text-gray-300 hidden sm:block">{user?.name || "User"}</span>
                <svg className={`w-4 h-4 text-gray-400 transition-transform ${profileOpen ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              <AnimatePresence>
                {profileOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className="absolute right-0 top-full mt-2 w-56 glass rounded-2xl border border-white/10 shadow-2xl overflow-hidden z-50 py-2"
                  >
                    <div className="px-4 py-3 border-b border-white/10">
                      <p className="font-bold text-white truncate">{user?.name}</p>
                      <p className="text-xs text-gray-400 truncate">{user?.email}</p>
                    </div>
                    <Link 
                      href="/profile" 
                      onClick={handleLogout}
                      className="block px-4 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/5 transition-colors flex items-center gap-2"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                      </svg>
                      Profile & Settings
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors flex items-center gap-2"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                      </svg>
                      Sign Out
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <button
              onClick={() => setAuthModalOpen(true)}
              className="px-4 py-2 rounded-xl bg-accent text-black font-bold text-sm hover:bg-accent/90 transition-colors hidden sm:block"
            >
              Sign In
            </button>
          )}

          <button 
            className="md:hidden p-2 text-white hover:text-gray-300 transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle Menu"
          >
            {mobileMenuOpen ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
            )}
          </button>
        </div>
      </nav>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed inset-0 z-40 bg-dark-900/95 backdrop-blur-xl pt-24 px-6 flex flex-col gap-6 md:hidden"
          >
            <div className="flex flex-col gap-8 text-2xl font-bold font-outfit uppercase tracking-widest text-center mt-12">
              <Link href="/?tab=movie" onClick={() => setMobileMenuOpen(false)} className="text-gray-300 hover:text-white transition-colors">Movies</Link>
              <Link href="/?tab=tv" onClick={() => setMobileMenuOpen(false)} className="text-gray-300 hover:text-white transition-colors">TV Shows</Link>
              <Link href="/vibes" onClick={() => setMobileMenuOpen(false)} className="text-gray-300 hover:text-white transition-colors">Vibes</Link>
              <Link href="/group" onClick={() => setMobileMenuOpen(false)} className="text-gray-300 hover:text-white transition-colors">Group Watch</Link>
            </div>
            <div className="pt-8 border-t border-white/10 flex flex-col gap-4">
              {isAuthenticated ? (
                <button onClick={handleLogout} className="text-red-400 text-center py-3 font-bold">Sign Out</button>
              ) : (
                <button onClick={() => { setMobileMenuOpen(false); setAuthModalOpen(true); }} className="bg-accent text-black py-3 rounded-lg font-bold">Sign In</button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
