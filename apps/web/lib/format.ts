/** Small formatting helpers shared across components. */

export const nf = new Intl.NumberFormat("en-US");

export function formatCount(n: number): string {
  return nf.format(n);
}

/** "4.2" — always one decimal, so ratings line up in a column. */
export function formatRating(n: number): string {
  return n.toFixed(1);
}

/** Milliseconds, readable: 71 ms / 1.2 s */
export function formatMs(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

/** Truncate on a word boundary rather than mid-word. */
export function truncate(text: string, max: number): string {
  if (!text || text.length <= max) return text;
  const cut = text.slice(0, max);
  const lastSpace = cut.lastIndexOf(" ");
  return `${cut.slice(0, lastSpace > max * 0.6 ? lastSpace : max)}…`;
}

/** Human label for a pipeline stage name. */
export const STAGE_LABELS: Record<string, string> = {
  multi_query: "Multi-query expansion",
  hyde: "HyDE",
  hybrid_retrieve: "Hybrid retrieval",
  rrf: "Reciprocal Rank Fusion",
  rerank: "Cross-encoder re-ranking",
};

/** One-line plain-English gloss for each stage, shown under the label. */
export const STAGE_PLAIN: Record<string, string> = {
  multi_query: "Asked your question three different ways and pooled the answers",
  hyde: "Wrote a description of the ideal book, then searched using that",
  hybrid_retrieve: "Searched by keyword, by meaning, and across related books at once",
  rrf: "Merged several ranked lists by position rather than by score",
  rerank: "Re-read the top results more carefully and reordered them",
};

export function stageLabel(name: string): string {
  return STAGE_LABELS[name] ?? name;
}
