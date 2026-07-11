import "./globals.css";
import Link from "next/link";
import { SearchModal } from "./SearchModal";

export const metadata = {
  title: "CinemaTime | Premium Recommendations",
  description: "AI Powered Movie & TV Search",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-dark-900 text-white min-h-screen flex flex-col antialiased">
        
        {/* Global Navigation Bar */}
        <nav className="fixed top-0 w-full z-50 glass border-b border-white/5 py-4 px-6 md:px-12 flex items-center justify-between transition-all duration-300">
          <Link href="/" className="flex items-center gap-1 group">
            <span className="text-3xl font-black tracking-widest uppercase font-outfit text-white group-hover:text-gray-200 transition-colors">
              CINEMA
            </span>
            <span className="text-4xl font-script text-[#00b4ff] -ml-2 mt-2 -rotate-2 group-hover:scale-105 transition-transform">
              Time
            </span>
          </Link>
          
          <div className="hidden md:flex items-center gap-8 font-semibold text-sm tracking-wide text-gray-300">
            <Link href="/?tab=movie" className="hover:text-white transition-colors">Movies</Link>
            <Link href="/?tab=tv" className="hover:text-white transition-colors">TV Shows</Link>
            <Link href="/?tab=anime" className="hover:text-white transition-colors">Anime</Link>
          </div>

          <SearchModal />
        </nav>

        {/* Main Content */}
        <div className="flex-1">
          {children}
        </div>

      </body>
    </html>
  );
}
