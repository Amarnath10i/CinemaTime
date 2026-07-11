import "./globals.css";

export const metadata = {
  title: "CineMatch – AI Movie Recommendations",
  description:
    "Discover your next favorite movie with state-of-the-art Sentence-BERT semantic search and FAISS vector similarity.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
