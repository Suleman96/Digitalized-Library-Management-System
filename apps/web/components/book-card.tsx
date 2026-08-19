"use client";

import { BookmarkPlus, Check, ExternalLink, Star } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { api } from "@/lib/api";
import { formatCount, formatRating, truncate } from "@/lib/format";
import type { Book } from "@/lib/types";

function Stars({ rating }: { rating: number }) {
  return (
    <span
      className="flex items-center gap-0.5"
      title={`${formatRating(rating)} out of 5`}
    >
      {[0, 1, 2, 3, 4].map((i) => (
        <Star
          key={i}
          className={`size-3 ${
            i < Math.round(rating)
              ? "fill-warning text-warning"
              : "text-hairline"
          }`}
        />
      ))}
    </span>
  );
}

function Cover({ book }: { book: Book }) {
  const [failed, setFailed] = useState(false);

  if (failed || !book.thumbnail) {
    return (
      <div className="grid h-full w-full place-items-center bg-surface-3 p-2">
        <span className="text-center font-display text-[11px] leading-tight text-ink-mute">
          {truncate(book.title, 42)}
        </span>
      </div>
    );
  }

  return (
    /* eslint-disable-next-line @next/next/no-img-element -- covers come from
       arbitrary third-party hosts; configuring next/image remotePatterns for
       every possible book CDN is not worth the deploy-time coupling. */
    <img
      src={book.thumbnail}
      alt=""
      loading="lazy"
      onError={() => setFailed(true)}
      className="h-full w-full object-cover"
    />
  );
}

export function BookCard({
  book,
  onSaved,
}: {
  book: Book;
  onSaved?: (book: Book) => void;
}) {
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  async function save(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (saved || saving) return;
    setSaving(true);
    try {
      await api.readingList.save(book);
      setSaved(true);
      onSaved?.(book);
    } finally {
      setSaving(false);
    }
  }

  const isExternal = !book.source.toLowerCase().includes("local");

  return (
    <article className="group relative flex gap-4 rounded-xl border border-hairline bg-surface p-4 shadow-card transition hover:border-brand/40 hover:shadow-raised">
      <Link
        href={`/book/${book.id}`}
        className="relative aspect-[2/3] w-[76px] shrink-0 overflow-hidden rounded-lg border border-hairline-soft bg-surface-2"
      >
        <Cover book={book} />
      </Link>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-start justify-between gap-2">
          <Link href={`/book/${book.id}`} className="min-w-0">
            <h3 className="font-display text-[15px] leading-snug font-semibold text-ink group-hover:text-brand">
              {truncate(book.title, 68)}
            </h3>
            <p className="mt-0.5 truncate text-[13px] text-ink-mute">
              {book.authors}
            </p>
          </Link>

          {book.average_rating > 0 && (
            <span className="tnum shrink-0 rounded-md bg-surface-2 px-1.5 py-0.5 font-mono text-[12px] font-semibold text-ink">
              {formatRating(book.average_rating)}
            </span>
          )}
        </div>

        <div className="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] text-ink-mute">
          {book.average_rating > 0 && <Stars rating={book.average_rating} />}
          {book.ratings_count > 0 && (
            <span className="tnum">{formatCount(book.ratings_count)} ratings</span>
          )}
          {book.published_year && <span className="tnum">{book.published_year}</span>}
          {book.num_pages > 0 && <span className="tnum">{book.num_pages} pp</span>}
        </div>

        {book.description && (
          <p className="mt-2 line-clamp-2 text-[13px] leading-relaxed text-ink-soft">
            {book.description}
          </p>
        )}

        <div className="mt-auto flex items-center gap-2 pt-3">
          <span
            className={`rounded-md px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide ${
              isExternal
                ? "bg-surface-2 text-ink-mute"
                : "bg-brand-wash text-brand"
            }`}
          >
            {isExternal ? "External" : "Library"}
          </span>

          {book.similarity > 0 && (
            <span
              className="tnum font-mono text-[10px] text-ink-mute"
              title="How closely this matched your query"
            >
              match {book.similarity.toFixed(2)}
            </span>
          )}

          <div className="ml-auto flex items-center gap-1">
            {book.info_link && book.info_link !== "#" && (
              <a
                href={book.info_link}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="grid size-7 place-items-center rounded-md text-ink-mute transition hover:bg-surface-2 hover:text-ink"
                title="Open the full record"
              >
                <ExternalLink className="size-3.5" />
              </a>
            )}
            <button
              type="button"
              onClick={save}
              disabled={saved || saving}
              className={`flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition ${
                saved
                  ? "bg-success-wash text-success"
                  : "text-ink-mute hover:bg-brand-wash hover:text-brand"
              }`}
              title={saved ? "In your reading list" : "Save to reading list"}
            >
              {saved ? (
                <>
                  <Check className="size-3.5" /> Saved
                </>
              ) : (
                <>
                  <BookmarkPlus className="size-3.5" /> Save
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

export function BookCardSkeleton() {
  return (
    <div className="flex gap-4 rounded-xl border border-hairline bg-surface p-4">
      <div className="skeleton aspect-[2/3] w-[76px] shrink-0 rounded-lg" />
      <div className="flex flex-1 flex-col gap-2">
        <div className="skeleton h-4 w-3/4 rounded" />
        <div className="skeleton h-3 w-1/2 rounded" />
        <div className="skeleton h-3 w-full rounded" />
        <div className="skeleton mt-auto h-3 w-1/3 rounded" />
      </div>
    </div>
  );
}
