"use client";

import { useQuery } from "@tanstack/react-query";
import { CornerDownLeft, Cpu, RotateCcw, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api, API_BASE } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

const PROMPTS = [
  "Find me books about ethical AI",
  "Suggest a thriller set in Cairo",
  "What is similar to Dune?",
  "Show me my reading list",
];

/** Friendly names for the agent's internal tools. */
const TOOL_LABELS: Record<string, string> = {
  search_worker: "Searching the library",
  curator_worker: "Managing your reading list",
};

export default function ConciergePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [threadId, setThreadId] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: llm } = useQuery({
    queryKey: ["llm-status"],
    queryFn: api.llm.status,
    retry: false,
  });

  useEffect(() => {
    setThreadId(
      globalThis.crypto?.randomUUID?.() ?? `t-${Date.now()}-${Math.random()}`,
    );
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const ready = llm?.capabilities?.agent ?? false;

  async function send(text?: string) {
    const message = (text ?? input).trim();
    if (!message || streaming || !ready) return;

    setInput("");
    setMessages((m) => [
      ...m,
      { role: "user", content: message },
      { role: "assistant", content: "", steps: [] },
    ]);
    setStreaming(true);

    try {
      const res = await fetch(`${API_BASE}/api/agent/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, threadId }),
      });

      if (!res.ok || !res.body) {
        throw new Error(
          res.status === 409
            ? "The assistant is not connected to an AI provider yet."
            : `The assistant could not respond (${res.status}).`,
        );
      }

      // Parse the SSE frames as they arrive.
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const eventLine = frame.match(/^event:\s*(.+)$/m);
          const dataLine = frame.match(/^data:\s*(.+)$/m);
          if (!eventLine || !dataLine) continue;

          const event = eventLine[1].trim();
          let payload: Record<string, string>;
          try {
            payload = JSON.parse(dataLine[1]);
          } catch {
            continue;
          }

          setMessages((prev) => {
            const next = [...prev];
            const last = { ...next[next.length - 1] };

            if (event === "token") {
              last.content += payload.text ?? "";
            } else if (event === "tool_call") {
              last.steps = [...(last.steps ?? []), { name: payload.name }];
            } else if (event === "tool_result") {
              last.steps = (last.steps ?? []).map((s) =>
                s.name === payload.name && !s.preview
                  ? { ...s, preview: payload.preview }
                  : s,
              );
            } else if (event === "done") {
              if (!last.content) last.content = payload.text ?? "";
            } else if (event === "error") {
              last.content = payload.message ?? "Something went wrong.";
            }

            next[next.length - 1] = last;
            return next;
          });
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          content: (err as Error).message,
        };
        return next;
      });
    } finally {
      setStreaming(false);
    }
  }

  function reset() {
    setMessages([]);
    setThreadId(
      globalThis.crypto?.randomUUID?.() ?? `t-${Date.now()}-${Math.random()}`,
    );
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-4rem)] w-full max-w-3xl flex-col px-4 py-6 sm:px-6">
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
            Ask the concierge
          </h1>
          <p className="mt-1 text-[13px] leading-relaxed text-ink-soft">
            A conversational assistant that decides for itself whether to search
            the library or manage your list — and shows you which it chose.
          </p>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={reset}
            className="flex shrink-0 items-center gap-1.5 rounded-lg border border-hairline px-2.5 py-1.5 text-[12px] font-medium text-ink-mute transition hover:border-brand hover:text-brand"
          >
            <RotateCcw className="size-3.5" /> New chat
          </button>
        )}
      </header>

      {!ready && (
        <div className="mb-4 flex gap-3 rounded-xl border border-warning/30 bg-warning-wash p-4">
          <Cpu className="mt-0.5 size-4 shrink-0 text-warning" />
          <div>
            <p className="text-[13px] font-semibold text-warning">
              No AI provider connected
            </p>
            <p className="mt-1 max-w-[60ch] text-[13px] leading-relaxed text-ink-soft">
              The conversational assistant needs a language model. Set{" "}
              <code className="rounded bg-surface-2 px-1 font-mono text-[12px]">
                LLM_PROVIDER
              </code>{" "}
              and{" "}
              <code className="rounded bg-surface-2 px-1 font-mono text-[12px]">
                LLM_MODEL
              </code>{" "}
              in your <code className="font-mono text-[12px]">.env</code>, or run
              Ollama locally. Everything else in the app works without one.
            </p>
          </div>
        </div>
      )}

      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto rounded-xl border border-hairline bg-surface p-4"
      >
        {messages.length === 0 && (
          <div className="grid h-full place-items-center py-10 text-center">
            <div>
              <p className="font-display text-lg text-ink">
                What are you in the mood to read?
              </p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {PROMPTS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => send(p)}
                    disabled={!ready}
                    className="rounded-full border border-hairline px-3 py-1.5 text-[12px] text-ink-soft transition hover:border-brand hover:text-brand disabled:opacity-40"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-xl px-3.5 py-2.5 ${
                m.role === "user"
                  ? "bg-brand text-brand-contrast"
                  : "bg-surface-2 text-ink"
              }`}
            >
              {m.steps && m.steps.length > 0 && (
                <div className="mb-2 space-y-1 border-b border-hairline pb-2">
                  {m.steps.map((s, j) => (
                    <p
                      key={j}
                      className="flex items-center gap-1.5 font-mono text-[11px] text-ink-mute"
                    >
                      <Wrench className="size-3" />
                      {TOOL_LABELS[s.name] ?? s.name}
                    </p>
                  ))}
                </div>
              )}
              <p className="text-[14px] leading-relaxed whitespace-pre-wrap">
                {m.content}
                {streaming && i === messages.length - 1 && (
                  <span className="ml-0.5 inline-block h-4 w-[2px] animate-pulse bg-current align-text-bottom" />
                )}
              </p>
            </div>
          </div>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="mt-3 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={!ready || streaming}
          placeholder={ready ? "Ask about anything…" : "Connect a provider first"}
          aria-label="Message the concierge"
          className="flex-1 rounded-xl border border-hairline bg-surface px-4 py-2.5 text-sm text-ink focus:border-brand disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!ready || streaming || !input.trim()}
          className="flex items-center gap-2 rounded-xl bg-brand px-4 text-sm font-semibold text-brand-contrast transition hover:bg-brand-hover disabled:opacity-40"
        >
          Send <CornerDownLeft className="size-3.5" />
        </button>
      </form>
    </div>
  );
}
