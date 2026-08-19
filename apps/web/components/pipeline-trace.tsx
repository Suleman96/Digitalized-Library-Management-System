"use client";

import { ChevronDown, Zap } from "lucide-react";
import { useState } from "react";

import { formatMs, STAGE_PLAIN, stageLabel } from "@/lib/format";
import type { PipelineTrace as Trace } from "@/lib/types";

/**
 * Renders what the retrieval engine actually did.
 *
 * This is the component that turns an invisible backend into something a
 * visitor can see: which stages ran, how many candidates each considered, and
 * what each cost in milliseconds.
 */
export function PipelineTrace({ trace }: { trace: Trace }) {
  const [open, setOpen] = useState(false);

  if (!trace.stages.length) return null;

  const slowest = Math.max(...trace.stages.map((s) => s.durationMs), 1);

  return (
    <div className="overflow-hidden rounded-xl border border-hairline bg-surface">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-surface-2"
      >
        <Zap className="size-4 shrink-0 text-brand" />
        <span className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-2">
          <span className="text-[13px] font-semibold text-ink">
            How this search ran
          </span>
          <span className="text-[12px] text-ink-mute">
            {trace.stages.length} stage{trace.stages.length === 1 ? "" : "s"} ·{" "}
            <span className="tnum">{formatMs(trace.totalMs)}</span>
          </span>
        </span>
        <ChevronDown
          className={`size-4 shrink-0 text-ink-mute transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {open && (
        <div className="border-t border-hairline-soft px-4 py-4">
          <p className="mb-4 max-w-[70ch] text-[13px] leading-relaxed text-ink-soft">
            Your search is not a single lookup. It runs through several stages,
            each narrowing or reordering the candidates. Here is exactly what
            happened, in order.
          </p>

          <ol className="space-y-3">
            {trace.stages.map((stage, i) => (
              <li key={`${stage.name}-${i}`} className="flex gap-3">
                <span className="tnum mt-0.5 grid size-6 shrink-0 place-items-center rounded-md bg-brand-wash font-mono text-[11px] font-bold text-brand">
                  {i + 1}
                </span>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                    <span className="text-[13px] font-semibold text-ink">
                      {stageLabel(stage.name)}
                    </span>
                    <span className="tnum shrink-0 font-mono text-[11px] text-ink-mute">
                      {formatMs(stage.durationMs)}
                    </span>
                  </div>

                  {STAGE_PLAIN[stage.name] && (
                    <p className="mt-0.5 text-[12px] text-ink-soft">
                      {STAGE_PLAIN[stage.name]}
                    </p>
                  )}

                  <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-surface-2">
                    <div
                      className="h-full rounded-full bg-brand/70"
                      style={{
                        width: `${Math.max(3, (stage.durationMs / slowest) * 100)}%`,
                      }}
                    />
                  </div>

                  <p className="mt-1.5 font-mono text-[11px] text-ink-mute">
                    <span className="tnum">{stage.candidates}</span> candidates
                    {stage.detail ? ` · ${stage.detail}` : ""}
                  </p>

                  {stage.topShift !== null && stage.topShift !== undefined && (
                    <p className="mt-1 text-[12px] text-warning">
                      Re-ranking moved the previous top result to position{" "}
                      <span className="tnum font-semibold">
                        {stage.topShift + 1}
                      </span>{" "}
                      — the careful pass disagreed with the fast one.
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>

          {trace.queryVariants.length > 0 && (
            <div className="mt-4 rounded-lg border border-hairline-soft bg-surface-2 p-3">
              <p className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-mute">
                Your question, rephrased by the AI
              </p>
              <ul className="space-y-1">
                {trace.queryVariants.map((v) => (
                  <li key={v} className="text-[13px] text-ink-soft">
                    &ldquo;{v}&rdquo;
                  </li>
                ))}
              </ul>
            </div>
          )}

          {trace.hydeDocument && (
            <div className="mt-3 rounded-lg border border-hairline-soft bg-surface-2 p-3">
              <p className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-mute">
                The imaginary &ldquo;perfect book&rdquo; it searched with
              </p>
              <p className="text-[13px] leading-relaxed text-ink-soft italic">
                {trace.hydeDocument}
              </p>
              <p className="mt-2 text-[12px] text-ink-mute">
                This description was invented, never shown as a result. Searching
                with a description finds better matches than searching with a
                short question.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
