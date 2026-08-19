"use client";

import { Info, SlidersHorizontal } from "lucide-react";
import { useState } from "react";

import type { LLMStatus, SearchRequest, SearchScope, SortBy } from "@/lib/types";

const LANGUAGES = ["Any", "English", "Arabic", "French", "German", "Spanish"];
const CATEGORIES = [
  "Any", "Adventure", "Biography", "Business", "Children", "Fantasy",
  "Fiction", "History", "Horror", "Mystery", "Non-Fiction", "Philosophy",
  "Poetry", "Romance", "Science", "Science Fiction", "Self-Help", "Thriller",
  "Travel", "Young Adult",
];

const SCOPES: { value: SearchScope; label: string; hint: string }[] = [
  { value: "both", label: "Everything", hint: "This library plus external catalogues" },
  { value: "local", label: "Library", hint: "Only the 6,800 books indexed here" },
  { value: "external", label: "External", hint: "Only Google Books and OpenLibrary" },
];

const SORTS: { value: SortBy; label: string }[] = [
  { value: "similarity", label: "Best match" },
  { value: "rating", label: "Highest rated" },
  { value: "year", label: "Newest" },
];

/** The four RAG toggles, each with a plain-English description. */
const AI_OPTIONS = [
  {
    key: "useAiExpansion" as const,
    label: "Expand my wording",
    hint: "The AI rewrites your request into richer search terms first.",
  },
  {
    key: "useHyde" as const,
    label: "Imagine the perfect book (HyDE)",
    hint: "Writes a description of the ideal book, then searches with that instead of your short question.",
  },
  {
    key: "useMultiQuery" as const,
    label: "Ask three ways at once",
    hint: "Rephrases your request three times and pools the results, so one unlucky phrasing cannot sink the search.",
  },
  {
    key: "useRerank" as const,
    label: "Re-read the top results",
    hint: "A slower, more careful model re-reads the best candidates and reorders them. Works without an AI provider.",
  },
];

export interface SearchPanelProps {
  value: SearchRequest;
  onChange: (next: SearchRequest) => void;
  onSubmit: () => void;
  pending: boolean;
  llm?: LLMStatus;
}

export function SearchPanel({
  value,
  onChange,
  onSubmit,
  pending,
  llm,
}: SearchPanelProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const set = <K extends keyof SearchRequest>(k: K, v: SearchRequest[K]) =>
    onChange({ ...value, [k]: v });

  const aiConnected = llm?.connected ?? false;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="space-y-4"
    >
      <div className="rounded-xl border border-hairline bg-surface p-4">
        <label
          htmlFor="scope"
          className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute"
        >
          Search where
        </label>
        <div className="grid grid-cols-3 gap-1 rounded-lg bg-surface-2 p-1">
          {SCOPES.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => set("scope", s.value)}
              title={s.hint}
              className={`truncate rounded-md px-2 py-1.5 text-[12px] font-medium whitespace-nowrap transition ${
                value.scope === s.value
                  ? "bg-surface text-ink shadow-card"
                  : "text-ink-mute hover:text-ink"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3 rounded-xl border border-hairline bg-surface p-4">
        <div>
          <label
            htmlFor="language"
            className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute"
          >
            Language
          </label>
          <select
            id="language"
            value={value.language}
            onChange={(e) => set("language", e.target.value)}
            className="w-full rounded-lg border border-hairline bg-surface px-3 py-2 text-sm text-ink"
          >
            {LANGUAGES.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="category"
            className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute"
          >
            Category
          </label>
          <select
            id="category"
            value={value.category}
            onChange={(e) => set("category", e.target.value)}
            className="w-full rounded-lg border border-hairline bg-surface px-3 py-2 text-sm text-ink"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="sort"
            className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute"
          >
            Order by
          </label>
          <select
            id="sort"
            value={value.sortBy}
            onChange={(e) => set("sortBy", e.target.value as SortBy)}
            className="w-full rounded-lg border border-hairline bg-surface px-3 py-2 text-sm text-ink"
          >
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="minRating"
            className="mb-1.5 flex items-baseline justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute"
          >
            Minimum rating
            <span className="tnum text-[11px] text-ink">
              {value.minRating?.toFixed(1) ?? "0.0"}
            </span>
          </label>
          <input
            id="minRating"
            type="range"
            min={0}
            max={5}
            step={0.5}
            value={value.minRating ?? 0}
            onChange={(e) => set("minRating", Number(e.target.value))}
            className="w-full accent-[var(--brand)]"
          />
        </div>
      </div>

      <div className="rounded-xl border border-hairline bg-surface">
        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          aria-expanded={showAdvanced}
          className="flex w-full items-center gap-2 px-4 py-3 text-left"
        >
          <SlidersHorizontal className="size-4 text-brand" />
          <span className="flex-1 text-[13px] font-semibold text-ink">
            Smarter searching
          </span>
          <span className="font-mono text-[10px] text-ink-mute">
            {showAdvanced ? "hide" : "show"}
          </span>
        </button>

        {showAdvanced && (
          <div className="space-y-3 border-t border-hairline-soft p-4">
            {!aiConnected && (
              <p className="flex gap-2 rounded-lg bg-warning-wash p-2.5 text-[12px] leading-relaxed text-warning">
                <Info className="mt-0.5 size-3.5 shrink-0" />
                <span>
                  Three of these need an AI provider connected. Without one,
                  ordinary search still works — and re-reading the top results
                  runs locally either way.
                </span>
              </p>
            )}

            {AI_OPTIONS.map((opt) => {
              const needsAi = opt.key !== "useRerank";
              const disabled = needsAi && !aiConnected;
              return (
                <label
                  key={opt.key}
                  className={`flex cursor-pointer gap-2.5 rounded-lg p-2 transition ${
                    disabled ? "opacity-45" : "hover:bg-surface-2"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={Boolean(value[opt.key])}
                    disabled={disabled}
                    onChange={(e) => set(opt.key, e.target.checked)}
                    className="mt-0.5 size-4 shrink-0 accent-[var(--brand)]"
                  />
                  <span className="min-w-0">
                    <span className="block text-[13px] font-medium text-ink">
                      {opt.label}
                    </span>
                    <span className="mt-0.5 block text-[12px] leading-relaxed text-ink-mute">
                      {opt.hint}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        )}
      </div>

      <button
        type="submit"
        disabled={pending || !value.query.trim()}
        className="w-full rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-brand-contrast transition hover:bg-brand-hover disabled:opacity-40"
      >
        {pending ? "Searching…" : "Search"}
      </button>
    </form>
  );
}
