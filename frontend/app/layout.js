import "./globals.css";

export const metadata = {
  title: "CineMatch – AI Movie Recommendations",
  description: "Discover your next favorite movie, TV show, or anime.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
