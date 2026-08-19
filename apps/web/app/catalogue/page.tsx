"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useEffect, useState } from "react";

import { BookCard, BookCardSkeleton } from "@/components/book-card";
import { api } from "@/lib/api";
import { formatCount } from "@/lib/format";

const PAGE_SIZE = 24;

export default function CataloguePage() {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  // Debounce so typing does not fire a request per keystroke.
  useEffect(() => {
    const t = setTimeout(() => {
      setQuery(input);
      setPage(1);
    }, 350);
    return () => clearTimeout(t);
  }, [input]);

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["catalogue", query, page],
    queryFn: () => api.books.browse({ q: query, page, pageSize: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="mx-auto w-full max-w-[1400px] px-4 py-8 sm:px-6">
      <header className="mb-6">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
          The catalogue
        </h1>
        <p className="mt-1.5 max-w-xl text-[14px] leading-relaxed text-ink-soft">
          Every book held locally. This is a plain alphabetical browse — filtering
          by title and author only, with no AI involved.
        </p>
      </header>

      <div className="relative mb-6 max-w-md">
        <Search className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-ink-mute" />
        <input
          type="search"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Filter by title or author…"
          aria-label="Filter by title or author"
          className="w-full rounded-xl border border-hairline bg-surface py-2.5 pr-4 pl-10 text-sm text-ink shadow-card focus:border-brand"
        />
      </div>

      {isError && (
        <p className="rounded-xl border border-danger/30 bg-danger-wash p-4 text-[13px] text-danger">
          {(error as Error).message}
        </p>
      )}

      {data && (
        <p className="mb-4 font-mono text-[11px] tracking-wide text-ink-mute">
          <span className="tnum">{formatCount(data.total)}</span> book
          {data.total === 1 ? "" : "s"}
          {query && <> matching &ldquo;{query}&rdquo;</>} · page{" "}
          <span className="tnum">{data.page}</span> of{" "}
          <span className="tnum">{data.pageCount}</span>
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {isPending
          ? Array.from({ length: 9 }).map((_, i) => <BookCardSkeleton key={i} />)
          : data?.items.map((b) => <BookCard key={b.id} book={b} />)}
      </div>

      {data && data.pageCount > 1 && (
        <nav
          className="mt-8 flex items-center justify-center gap-2"
          aria-label="Pagination"
        >
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="flex items-center gap-1 rounded-lg border border-hairline bg-surface px-3 py-2 text-[13px] font-medium text-ink-soft transition hover:border-brand hover:text-brand disabled:opacity-40"
          >
            <ChevronLeft className="size-4" /> Previous
          </button>
          <span className="tnum px-3 font-mono text-[12px] text-ink-mute">
            {data.page} / {data.pageCount}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(data.pageCount, p + 1))}
            disabled={page >= data.pageCount}
            className="flex items-center gap-1 rounded-lg border border-hairline bg-surface px-3 py-2 text-[13px] font-medium text-ink-soft transition hover:border-brand hover:text-brand disabled:opacity-40"
          >
            Next <ChevronRight className="size-4" />
          </button>
        </nav>
      )}
    </div>
  );
}
