import "./globals.css";
import { Navbar } from "../components/Navbar";

export const metadata = {
  title: "CinemaTime | Recommendations",
  description: "AI Powered Movie & TV Search",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-dark-900 text-white min-h-screen flex flex-col antialiased">
        
        <Navbar />

        {/* Main Content */}
        <div className="flex-1">
          {children}
        </div>

      </body>
    </html>
  );
}
