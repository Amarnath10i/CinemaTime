"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

const STAGES = [
  { name: "EASE", body: "Linear item-to-item model with a closed-form solution; likes weighted by recency." },
  { name: "ALS fold-in", body: "Implicit matrix factorization. Your taste vector is solved from your likes at request time; new releases get factors from their plot embeddings." },
  { name: "Content", body: "Sentence-BERT embeddings of plots and tags: works for films nobody has rated yet." },
  { name: "Popularity", body: "What was most liked over the last year of data." },
];

const pct = (x) => (x === undefined || x === null ? "–" : x.toFixed(3));

function Table({ head, rows }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 uppercase text-[11px] tracking-wider border-b border-white/10">
            {head.map((h, i) => <th key={h} className={`py-2 pr-4 font-semibold ${i ? "text-right" : ""}`}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={`border-b border-white/5 ${r.highlight ? "text-white font-semibold" : "text-gray-300"}`}>
              {r.cells.map((c, j) => <td key={j} className={`py-2 pr-4 ${j ? "text-right tabular-nums" : ""}`}>{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function HowItWorksPage() {
  const [card, setCard] = useState(null);

  useEffect(() => {
    fetch("/api/model-card").then((r) => r.json()).then(setCard).catch(() => setCard({ available: false }));
  }, []);

  const offline = card?.offline;
  const replay = card?.replay;
  const models = offline ? Object.entries(offline.models) : [];
  const best = models.length ? Math.max(...models.map(([, m]) => m["ndcg@20"])) : 0;

  return (
    <main className="min-h-screen bg-dark-900 pb-24 pt-28 px-6 md:px-12">
      <div className="max-w-5xl mx-auto space-y-12">
        <header>
          <h1 className="text-4xl md:text-6xl font-black font-outfit uppercase tracking-tighter text-white">
            How <span className="text-[#00b4ff]">For You</span> works
          </h1>
          <p className="text-gray-400 mt-4 text-lg max-w-3xl">
            A two-stage recommender trained offline on MovieLens 32M joined to this catalog through TMDB ids,
            evaluated on a later year it never saw, and served here with NumPy only.{" "}
            <Link href="/for-you" className="text-[#00b4ff] hover:underline">Try it →</Link>
          </p>
        </header>

        <section>
          <h2 className="text-2xl font-bold font-outfit mb-4">1 · Candidates from four retrievers</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {STAGES.map((s) => (
              <div key={s.name} className="glass rounded-xl p-4">
                <p className="font-bold text-white mb-1">{s.name}</p>
                <p className="text-sm text-gray-400 leading-snug">{s.body}</p>
              </div>
            ))}
          </div>
          <h2 className="text-2xl font-bold font-outfit mt-8 mb-3">2 · One learned ranking</h2>
          <p className="text-gray-300 max-w-3xl">
            A LightGBM LambdaRank model{card?.ranker ? ` (${card.ranker.trees} trees)` : ""} orders the few hundred candidates
            using every retriever&apos;s score and rank, release age, whether anyone has rated the film yet, genre overlap
            with your likes and how far its era is from yours. It optimizes NDCG directly. Explanations come from EASE:
            its scores are exact sums of one contribution per liked movie, so &ldquo;Because you liked X&rdquo; names the
            largest one.
          </p>
        </section>

        {card && !card.available && (
          <p className="text-gray-400">The model is not deployed on this server yet, so there are no numbers to show.</p>
        )}

        {offline && (
          <section>
            <h2 className="text-2xl font-bold font-outfit mb-2">3 · Evaluated on the future</h2>
            <p className="text-gray-400 mb-5 max-w-3xl">
              Trained on likes (4+ stars) before {offline.fold.train_until}; scored on what{" "}
              {offline.fold.users.toLocaleString()} users went on to like until {offline.fold.evaluate_until}{" "}
              ({offline.fold.held_out_likes.toLocaleString()} likes). Every model ranks the whole catalog; no sampled negatives.
            </p>
            <div className="glass rounded-xl p-4">
              <Table
                head={["model", "NDCG@20", "Recall@20", "Hit@10", "Coverage@10"]}
                rows={models.map(([name, m]) => ({
                  highlight: m["ndcg@20"] === best,
                  cells: [name, pct(m["ndcg@20"]), pct(m["recall@20"]), pct(m["hit@10"]), pct(m.coverage)],
                }))}
              />
            </div>
          </section>
        )}

        {replay && (
          <section>
            <h2 className="text-2xl font-bold font-outfit mb-2">4 · What is served is what was measured</h2>
            <p className="text-gray-400 mb-5 max-w-3xl">
              The test users were replayed through this API&apos;s engine: NDCG@20 {pct(replay["ndcg@20"])} served vs{" "}
              {pct(replay["offline_ndcg@20"])} offline, keeping each movie&apos;s top {replay.ease_keep} EASE weights. One request
              takes {replay.latency_ms.p50.toFixed(0)} ms at the median, {replay.latency_ms.p95.toFixed(0)} ms at p95.
              How each method does when a visitor has given only a few likes:
            </p>
            <div className="glass rounded-xl p-4">
              <Table
                head={Object.keys(replay["short_history_ndcg@20"][0]).map((k) => (k === "likes given" ? "likes given" : k))}
                rows={replay["short_history_ndcg@20"].map((r) => ({
                  cells: Object.entries(r).map(([k, v]) => (k === "likes given" ? v : pct(v))),
                }))}
              />
            </div>
            <p className="text-xs text-gray-500 mt-3">NDCG@20 on the held-out year, using only each user&apos;s most recent likes.</p>
          </section>
        )}

        {card?.available && (
          <section className="text-sm text-gray-500">
            Ratings data ends {card.interactions_until}; films released since are ranked as cold-start items from their
            plot embeddings. Exported {card.exported}. Source and full reports: <code>ml/</code> in the repository.
          </section>
        )}
      </div>
    </main>
  );
}
