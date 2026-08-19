"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookMarked, Download, Trash2 } from "lucide-react";
import Link from "next/link";

import { BookCard, BookCardSkeleton } from "@/components/book-card";
import { api, API_BASE } from "@/lib/api";
import type { Book } from "@/lib/types";

export default function ReadingListPage() {
  const qc = useQueryClient();

  const list = useQuery({
    queryKey: ["reading-list"],
    queryFn: api.readingList.all,
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.readingList.remove(id),
    // Optimistic: drop it immediately, restore if the server disagrees.
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ["reading-list"] });
      const previous = qc.getQueryData<Book[]>(["reading-list"]);
      qc.setQueryData<Book[]>(["reading-list"], (old) =>
        (old ?? []).filter((b) => b.id !== id),
      );
      return { previous };
    },
    onError: (_e, _id, ctx) => {
      if (ctx?.previous) qc.setQueryData(["reading-list"], ctx.previous);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["reading-list"] }),
  });

  const clear = useMutation({
    mutationFn: api.readingList.clear,
    onSuccess: () => qc.setQueryData(["reading-list"], []),
  });

  async function exportPdf() {
    const res = await fetch(`${API_BASE}/api/reading-list/export`, {
      method: "POST",
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "iqra-reading-list.pdf";
    a.click();
    URL.revokeObjectURL(url);
  }

  const books = list.data ?? [];

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
            Your reading list
          </h1>
          <p className="mt-1.5 text-[14px] text-ink-soft">
            Books you saved while searching. Stored on the server, so it survives
            a refresh.
          </p>
        </div>

        {books.length > 0 && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={exportPdf}
              className="flex items-center gap-2 rounded-lg border border-hairline bg-surface px-3 py-2 text-[13px] font-medium text-ink-soft transition hover:border-brand hover:text-brand"
            >
              <Download className="size-4" /> Export PDF
            </button>
            <button
              type="button"
              onClick={() => clear.mutate()}
              className="flex items-center gap-2 rounded-lg border border-danger/30 px-3 py-2 text-[13px] font-medium text-danger transition hover:bg-danger-wash"
            >
              <Trash2 className="size-4" /> Clear all
            </button>
          </div>
        )}
      </header>

      {list.isPending && (
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <BookCardSkeleton key={i} />
          ))}
        </div>
      )}

      {!list.isPending && books.length === 0 && (
        <div className="rounded-xl border border-dashed border-hairline p-14 text-center">
          <BookMarked className="mx-auto size-8 text-ink-mute" />
          <h2 className="mt-4 font-display text-lg font-semibold text-ink">
            Nothing saved yet
          </h2>
          <p className="mx-auto mt-2 max-w-sm text-[13px] leading-relaxed text-ink-soft">
            Search for something, then press Save on any result to build a
            shortlist you can export.
          </p>
          <Link
            href="/"
            className="mt-5 inline-block rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-brand-contrast transition hover:bg-brand-hover"
          >
            Start searching
          </Link>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {books.map((b) => (
          <div key={b.id} className="relative">
            <BookCard book={b} />
            <button
              type="button"
              onClick={() => remove.mutate(b.id)}
              className="absolute top-2 right-2 grid size-7 place-items-center rounded-md bg-surface/90 text-ink-mute opacity-0 transition hover:bg-danger-wash hover:text-danger focus-visible:opacity-100 group-hover:opacity-100 [article:hover~&]:opacity-100"
              title="Remove from list"
              aria-label={`Remove ${b.title} from your reading list`}
            >
              <Trash2 className="size-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
