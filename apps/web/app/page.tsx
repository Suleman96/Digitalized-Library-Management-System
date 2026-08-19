"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertCircle, Search } from "lucide-react";
import { useState } from "react";

import { BookCard, BookCardSkeleton } from "@/components/book-card";
import { PipelineTrace } from "@/components/pipeline-trace";
import { SearchPanel } from "@/components/search-panel";
import { api, ApiError } from "@/lib/api";
import type { SearchRequest, SearchResponse } from "@/lib/types";

const EXAMPLES = [
  "A gripping mystery set in the Middle East",
  "Books that explain artificial intelligence clearly",
  "Leadership books for first-time managers",
  "Hands-on science for curious teenagers",
];

const DEFAULTS: SearchRequest = {
  query: "",
  language: "Any",
  category: "Any",
  localLimit: 12,
  externalLimit: 6,
  minRating: 0,
  scope: "both",
  sortBy: "similarity",
  useAiExpansion: false,
  useHyde: false,
  useMultiQuery: false,
  useRerank: false,
};

export default function DiscoverPage() {
  const [form, setForm] = useState<SearchRequest>(DEFAULTS);
  const [results, setResults] = useState<SearchResponse | null>(null);

  const { data: llm } = useQuery({
    queryKey: ["llm-status"],
    queryFn: api.llm.status,
    retry: false,
  });

  const search = useMutation({
    mutationFn: (req: SearchRequest) => api.search(req),
    onSuccess: setResults,
  });

  function run(query?: string) {
    const next = query ? { ...form, query } : form;
    if (query) setForm(next);
    if (!next.query.trim()) return;
    search.mutate(next);
  }

  const error = search.error as ApiError | null;
  const total = results ? results.local.length + results.external.length : 0;

  return (
    <div className="mx-auto w-full max-w-[1400px] px-4 py-8 sm:px-6">
      {/* ---------- Hero ---------- */}
      {!results && !search.isPending && (
        <section className="mx-auto mb-10 max-w-2xl text-center animate-rise">
          <h1 className="font-display text-4xl leading-[1.1] font-semibold tracking-tight text-ink sm:text-5xl">
            Find books by what you mean
          </h1>
          <p className="mx-auto mt-4 max-w-lg text-[15px] leading-relaxed text-ink-soft">
            Describe the book you want in your own words — a mood, a theme, a
            reader. You do not need to know the title, the author, or the right
            keywords.
          </p>
        </section>
      )}

      {/* ---------- Search bar ---------- */}
      <div className="mx-auto mb-8 max-w-3xl">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-ink-mute" />
            <input
              type="search"
              value={form.query}
              onChange={(e) => setForm({ ...form, query: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && run()}
              placeholder="Describe the book you're looking for…"
              aria-label="Describe the book you're looking for"
              className="w-full rounded-xl border border-hairline bg-surface py-3 pr-4 pl-10 text-[15px] text-ink shadow-card transition placeholder:text-ink-mute focus:border-brand"
            />
          </div>
          <button
            type="button"
            onClick={() => run()}
            disabled={search.isPending || !form.query.trim()}
            className="rounded-xl bg-brand px-6 text-sm font-semibold text-brand-contrast transition hover:bg-brand-hover disabled:opacity-40"
          >
            {search.isPending ? "Searching…" : "Search"}
          </button>
        </div>

        {!results && (
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => run(ex)}
                className="rounded-full border border-hairline bg-surface px-3 py-1.5 text-[12px] text-ink-soft transition hover:border-brand hover:text-brand"
              >
                {ex}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* ---------- Filters ---------- */}
        <aside className="lg:sticky lg:top-24 lg:self-start">
          <SearchPanel
            value={form}
            onChange={setForm}
            onSubmit={() => run()}
            pending={search.isPending}
            llm={llm}
          />
        </aside>

        {/* ---------- Results ---------- */}
        <section className="min-w-0">
          {error && (
            <div className="mb-4 flex gap-3 rounded-xl border border-danger/30 bg-danger-wash p-4">
              <AlertCircle className="mt-0.5 size-4 shrink-0 text-danger" />
              <div className="min-w-0">
                <p className="text-[13px] font-semibold text-danger">
                  {error.isStarting
                    ? "The engine is still starting"
                    : "That search did not work"}
                </p>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-soft">
                  {error.message}
                </p>
              </div>
            </div>
          )}

          {search.isPending && (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <BookCardSkeleton key={i} />
              ))}
            </div>
          )}

          {results && !search.isPending && (
            <div className="space-y-6 animate-rise">
              <PipelineTrace trace={results.trace} />

              {results.expandedQuery && (
                <p className="rounded-lg border border-hairline-soft bg-surface-2 px-3 py-2 text-[12px] text-ink-soft">
                  The AI searched for{" "}
                  <span className="font-medium text-ink">
                    &ldquo;{results.expandedQuery}&rdquo;
                  </span>{" "}
                  rather than your exact wording.
                </p>
              )}

              {total === 0 && (
                <div className="rounded-xl border border-hairline bg-surface p-10 text-center">
                  <h3 className="font-display text-lg font-semibold text-ink">
                    Nothing matched
                  </h3>
                  <p className="mx-auto mt-2 max-w-sm text-[13px] leading-relaxed text-ink-soft">
                    Try describing the book differently, lowering the minimum
                    rating, or widening the search to external catalogues.
                  </p>
                </div>
              )}

              {results.local.length > 0 && (
                <ResultGroup
                  title="From this library"
                  caption="Indexed locally and searched with the full pipeline"
                  books={results.local}
                />
              )}

              {results.external.length > 0 && (
                <ResultGroup
                  title="From external catalogues"
                  caption="Google Books and OpenLibrary, re-ranked for relevance"
                  books={results.external}
                />
              )}
            </div>
          )}

          {!results && !search.isPending && !error && (
            <div className="rounded-xl border border-dashed border-hairline p-12 text-center">
              <p className="font-display text-lg text-ink">
                Your results will appear here
              </p>
              <p className="mx-auto mt-2 max-w-sm text-[13px] leading-relaxed text-ink-soft">
                Every search also shows exactly how it was answered — which
                stages ran, and what each one cost.
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function ResultGroup({
  title,
  caption,
  books,
}: {
  title: string;
  caption: string;
  books: SearchResponse["local"];
}) {
  return (
    <section>
      <div className="mb-3 flex items-baseline justify-between gap-3 border-b border-hairline pb-2">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">{title}</h2>
          <p className="text-[12px] text-ink-mute">{caption}</p>
        </div>
        <span className="tnum shrink-0 font-mono text-[11px] text-ink-mute">
          {books.length} result{books.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {books.map((b) => (
          <BookCard key={b.id} book={b} />
        ))}
      </div>
    </section>
  );
}
