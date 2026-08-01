import "./globals.css";
import { Navbar } from "../components/Navbar";
import { SubscriptionProvider } from "../context/SubscriptionContext";

export const metadata = {
  title: "CinemaTime | Recommendations",
  description: "AI Powered Movie & TV Search",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-dark-900 text-white min-h-screen flex flex-col antialiased">
        <SubscriptionProvider>
          <Navbar />
  
          {/* Main Content */}
          <div className="flex-1">
            {children}
          </div>
        </SubscriptionProvider>
      </body>
    </html>
  );
}
