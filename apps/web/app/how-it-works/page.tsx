import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "How it works",
  description:
    "A plain-English explanation of how Iqra finds books by meaning rather than keywords.",
};

const STEPS = [
  {
    n: "01",
    title: "Two searches run at the same time",
    plain:
      "One search matches words, the way Ctrl+F does — but smarter about which words actually matter. The other matches meaning: it knows a “Cairo thriller” and an “Egyptian suspense novel” are the same idea even though they share no words.",
    why: "Each one fails where the other succeeds. Word-matching misses anything you phrased differently. Meaning-matching misses exact things like an unusual author's name. Running both and combining them beats either alone.",
    technical: "BM25Okapi + FAISS IndexFlatIP, weighted 40/60 after per-query min-max normalisation",
  },
  {
    n: "02",
    title: "A map of how books relate to each other",
    plain:
      "Beyond the two searches, the system holds a web of connections — which books share an author, which share a subject. It can walk those links to reach a good match that neither search would have found on its own.",
    why: "Some of the best recommendations are one step removed from what you asked for.",
    technical: "NetworkX graph — 6,810 nodes, 69,116 author and category edges, cached to disk",
  },
  {
    n: "03",
    title: "The lists get merged fairly",
    plain:
      "Now there are several ranked lists of candidates. You cannot simply average their scores, because each search scores on its own scale — like adding a temperature in Celsius to one in Fahrenheit. So the system throws the scores away and uses positions instead. A book near the top of several lists wins.",
    why: "It means no single search can dominate just because it happens to produce bigger numbers.",
    technical: "Reciprocal Rank Fusion, score = Σ 1/(rank + 60)",
  },
  {
    n: "04",
    title: "Optionally, the AI writes a fake perfect book first",
    plain:
      "Your question is maybe five words. A book description is two hundred. Comparing them is lopsided. So the AI writes a short description of the book that would perfectly answer your request, and the system searches using that instead — comparing a description against descriptions.",
    why: "The invented book is never shown to you. It is scaffolding, and it does not need to be factually true — it only needs to land in the right neighbourhood.",
    technical: "HyDE — Hypothetical Document Embeddings",
  },
  {
    n: "05",
    title: "Optionally, your question gets asked three ways",
    plain:
      "Your exact phrasing might be unlucky. The AI rewrites your request three different ways, searches with all of them, and trusts the books that keep showing up across all three.",
    why: "It is a cheap consensus check against one bad wording sinking an otherwise good search.",
    technical: "Multi-query expansion, results merged by RRF",
  },
  {
    n: "06",
    title: "A slower, more careful reader checks the top results",
    plain:
      "The first search is fast but rough: it looks at your question and each book separately, then compares the two summaries. A second model reads your question and each book together, in full — far more accurate, but far too slow to run across all 6,810 books.",
    why: "So it only re-reads the best handful and reorders them. Fast and rough to narrow down; slow and careful to finish. This is the single biggest accuracy gain in the whole pipeline.",
    technical: "Cross-encoder re-ranking, ms-marco-MiniLM-L-6-v2",
  },
];

export default function HowItWorksPage() {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
      <header className="mb-10">
        <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.16em] text-brand">
          How it works
        </p>
        <h1 className="font-display text-4xl leading-[1.1] font-semibold tracking-tight text-ink">
          Finding a book you cannot name
        </h1>
        <p className="mt-4 max-w-[62ch] text-[15px] leading-relaxed text-ink-soft">
          Imagine a librarian who has read every book in the building. You say
          &ldquo;something gripping, a mystery, set somewhere in the Middle
          East.&rdquo; You have not given a title, an author, or a category — and
          an ordinary computer search would fail completely, because you used
          none of the words printed on the books.
        </p>
        <p className="mt-3 max-w-[62ch] text-[15px] leading-relaxed text-ink-soft">
          That is the problem this system solves. Here is how, in six steps.
        </p>
      </header>

      <ol className="space-y-8">
        {STEPS.map((s) => (
          <li key={s.n} className="flex gap-4">
            <span className="tnum shrink-0 font-mono text-[13px] font-bold text-brand">
              {s.n}
            </span>
            <div className="min-w-0">
              <h2 className="font-display text-xl leading-snug font-semibold text-ink">
                {s.title}
              </h2>
              <p className="mt-2 max-w-[62ch] text-[14px] leading-relaxed text-ink-soft">
                {s.plain}
              </p>
              <p className="mt-2 max-w-[62ch] text-[14px] leading-relaxed text-ink-mute">
                {s.why}
              </p>
              <p className="mt-3 inline-block rounded-md bg-surface-2 px-2 py-1 font-mono text-[11px] text-ink-mute">
                {s.technical}
              </p>
            </div>
          </li>
        ))}
      </ol>

      <section className="mt-12 rounded-xl border border-hairline bg-surface p-6">
        <h2 className="font-display text-xl font-semibold text-ink">
          Why any of this matters
        </h2>
        <p className="mt-3 max-w-[62ch] text-[14px] leading-relaxed text-ink-soft">
          Steps 4, 5, and 6 are optional, and they cost time. Step 6 adds a
          fraction of a second. Steps 4 and 5 each require a round trip to an AI
          model, which can take a second or more.
        </p>
        <p className="mt-3 max-w-[62ch] text-[14px] leading-relaxed text-ink-soft">
          That is a genuine trade-off, which is why they are switches rather than
          defaults — and why every search shows you exactly what it ran and what
          each stage cost. Turn them on, watch the trace, and decide for yourself
          whether the better results were worth the wait.
        </p>
        <Link
          href="/"
          className="mt-5 inline-block rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-brand-contrast transition hover:bg-brand-hover"
        >
          Try a search
        </Link>
      </section>

      <section className="mt-6 rounded-xl border border-hairline-soft bg-surface-2 p-6">
        <h2 className="font-display text-lg font-semibold text-ink">
          What runs without AI
        </h2>
        <p className="mt-2 max-w-[62ch] text-[14px] leading-relaxed text-ink-soft">
          Steps 1, 2, 3, and 6 need no AI provider at all — they run entirely on
          the server. So searching, browsing, saving, and the analytics all work
          out of the box. Connecting a provider adds the query rewriting, the
          imaginary-book trick, and the conversational assistant.
        </p>
      </section>
    </div>
  );
}
