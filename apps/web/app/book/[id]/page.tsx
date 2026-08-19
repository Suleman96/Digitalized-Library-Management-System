"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, BookmarkPlus, Check, ExternalLink, Star } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { BookCard, BookCardSkeleton } from "@/components/book-card";
import { api } from "@/lib/api";
import { formatCount, formatRating } from "@/lib/format";

export default function BookDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [saved, setSaved] = useState(false);
  const [coverFailed, setCoverFailed] = useState(false);

  const book = useQuery({
    queryKey: ["book", id],
    queryFn: () => api.books.get(id),
  });

  const similar = useQuery({
    queryKey: ["similar", id],
    queryFn: () => api.books.similar(id, 6),
    enabled: Boolean(book.data),
  });

  const save = useMutation({
    mutationFn: () => api.readingList.save(book.data!),
    onSuccess: () => setSaved(true),
  });

  if (book.isPending) {
    return (
      <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
        <div className="flex gap-8">
          <div className="skeleton aspect-[2/3] w-48 shrink-0 rounded-xl" />
          <div className="flex-1 space-y-3">
            <div className="skeleton h-8 w-3/4 rounded" />
            <div className="skeleton h-4 w-1/3 rounded" />
            <div className="skeleton h-24 w-full rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (book.isError || !book.data) {
    return (
      <div className="mx-auto w-full max-w-2xl px-4 py-20 text-center sm:px-6">
        <h1 className="font-display text-2xl font-semibold text-ink">
          That book is not here
        </h1>
        <p className="mt-2 text-[14px] text-ink-soft">
          It may have been removed from the catalogue, or the link may be wrong.
        </p>
        <Link
          href="/catalogue"
          className="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-brand-contrast"
        >
          <ArrowLeft className="size-4" /> Browse the catalogue
        </Link>
      </div>
    );
  }

  const b = book.data;

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <Link
        href="/catalogue"
        className="mb-6 inline-flex items-center gap-1.5 text-[13px] font-medium text-ink-mute transition hover:text-brand"
      >
        <ArrowLeft className="size-4" /> Back to the catalogue
      </Link>

      <article className="flex flex-col gap-8 sm:flex-row">
        <div className="mx-auto w-44 shrink-0 sm:mx-0">
          <div className="aspect-[2/3] overflow-hidden rounded-xl border border-hairline bg-surface-2 shadow-raised">
            {coverFailed || !b.thumbnail ? (
              <div className="grid h-full place-items-center p-4">
                <span className="text-center font-display text-sm text-ink-mute">
                  {b.title}
                </span>
              </div>
            ) : (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={b.thumbnail}
                alt=""
                referrerPolicy="no-referrer"
                onError={() => setCoverFailed(true)}
                className="h-full w-full object-cover"
              />
            )}
          </div>

          <button
            type="button"
            onClick={() => save.mutate()}
            disabled={saved || save.isPending}
            className={`mt-3 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition ${
              saved
                ? "bg-success-wash text-success"
                : "bg-brand text-brand-contrast hover:bg-brand-hover"
            }`}
          >
            {saved ? (
              <>
                <Check className="size-4" /> In your list
              </>
            ) : (
              <>
                <BookmarkPlus className="size-4" /> Save to reading list
              </>
            )}
          </button>

          {b.info_link && b.info_link !== "#" && (
            <a
              href={b.info_link}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-hairline px-4 py-2 text-[13px] font-medium text-ink-soft transition hover:border-brand hover:text-brand"
            >
              <ExternalLink className="size-3.5" /> Full record
            </a>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <h1 className="font-display text-3xl leading-tight font-semibold tracking-tight text-ink">
            {b.title}
          </h1>
          {b.subtitle && (
            <p className="mt-1 font-display text-lg text-ink-soft">{b.subtitle}</p>
          )}
          <p className="mt-2 text-[15px] text-ink-soft">{b.authors}</p>

          {b.average_rating > 0 && (
            <div className="mt-4 flex items-center gap-3">
              <span className="flex items-center gap-0.5">
                {[0, 1, 2, 3, 4].map((i) => (
                  <Star
                    key={i}
                    className={`size-4 ${
                      i < Math.round(b.average_rating)
                        ? "fill-warning text-warning"
                        : "text-hairline"
                    }`}
                  />
                ))}
              </span>
              <span className="tnum font-mono text-sm font-semibold text-ink">
                {formatRating(b.average_rating)}
              </span>
              {b.ratings_count > 0 && (
                <span className="tnum text-[13px] text-ink-mute">
                  {formatCount(b.ratings_count)} ratings
                </span>
              )}
            </div>
          )}

          <dl className="mt-6 grid grid-cols-2 gap-4 rounded-xl border border-hairline bg-surface p-4 sm:grid-cols-4">
            <Fact label="Published" value={b.published_year || "—"} />
            <Fact label="Pages" value={b.num_pages ? formatCount(b.num_pages) : "—"} />
            <Fact label="Language" value={b.language.toUpperCase() || "—"} />
            <Fact label="Source" value={b.source || "—"} />
          </dl>

          {b.categories && (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {b.categories
                .split(",")
                .map((c) => c.trim())
                .filter(Boolean)
                .slice(0, 6)
                .map((c) => (
                  <span
                    key={c}
                    className="rounded-full bg-brand-wash px-2.5 py-1 text-[11px] font-medium text-brand"
                  >
                    {c}
                  </span>
                ))}
            </div>
          )}

          {b.description && (
            <div className="mt-6">
              <h2 className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute">
                Description
              </h2>
              <p className="max-w-[68ch] text-[14px] leading-relaxed text-ink-soft">
                {b.description}
              </p>
            </div>
          )}
        </div>
      </article>

      <section className="mt-12">
        <div className="mb-3 border-b border-hairline pb-2">
          <h2 className="font-display text-xl font-semibold text-ink">
            Readers who liked this
          </h2>
          <p className="text-[12px] text-ink-mute">
            Found by meaning, not by category — these are the closest books in the
            library.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {similar.isPending
            ? Array.from({ length: 4 }).map((_, i) => <BookCardSkeleton key={i} />)
            : similar.data?.map((s) => <BookCard key={s.id} book={s} />)}
        </div>
      </section>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-mute">
        {label}
      </dt>
      <dd className="tnum mt-1 truncate text-[14px] font-medium text-ink" title={value}>
        {value}
      </dd>
    </div>
  );
}
