"use client";
import { useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { AIAssistant } from "./AIAssistant";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
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
          <Link href="/?tab=anime" className="hover:text-white transition-colors hover:scale-105 transform">Anime</Link>
        </div>

        <div className="flex items-center gap-4">
          <AIAssistant />
          
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
              <Link href="/?tab=anime" onClick={() => setMobileMenuOpen(false)} className="text-gray-300 hover:text-white transition-colors">Anime</Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
