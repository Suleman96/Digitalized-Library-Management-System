"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  BookMarked,
  Library,
  Menu,
  MessageSquare,
  Moon,
  Search,
  Sparkles,
  Sun,
  X,
} from "lucide-react";
import { useTheme } from "next-themes";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api";
import { formatCount } from "@/lib/format";

const NAV = [
  { href: "/", label: "Discover", icon: Search },
  { href: "/catalogue", label: "Catalogue", icon: Library },
  { href: "/concierge", label: "Concierge", icon: MessageSquare },
  { href: "/reading-list", label: "Reading list", icon: BookMarked },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/how-it-works", label: "How it works", icon: Sparkles },
] as const;

/** The DiploTech bar mark, drawn rather than loaded, so it inherits theme colour. */
function Logomark() {
  return (
    <span className="flex items-end gap-[2px]" aria-hidden>
      <span className="block h-[11px] w-[4px] rounded-[1px] bg-[#165491]" />
      <span className="block h-[16px] w-[4px] rounded-[1px] bg-ink" />
      <span className="block h-[19px] w-[4px] rounded-[1px] bg-[#ED1C24]" />
    </span>
  );
}

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      className="grid size-9 place-items-center rounded-lg border border-hairline bg-surface text-ink-mute transition hover:border-brand hover:text-brand"
      aria-label="Toggle colour theme"
      title="Toggle colour theme"
    >
      <Moon className="size-4 dark:hidden" />
      <Sun className="hidden size-4 dark:block" />
    </button>
  );
}

/** Live engine state, so a cold or unreachable API is never a mystery. */
function EngineStatus() {
  const { data, isError, error } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: (q) => (q.state.data?.status === "ok" ? false : 4000),
  });

  if (isError) {
    return (
      <span
        className="hidden items-center gap-2 rounded-lg border border-danger/30 bg-danger-wash px-2.5 py-1.5 text-xs font-medium text-danger sm:flex"
        title={(error as Error)?.message}
      >
        <span className="size-1.5 rounded-full bg-danger" />
        API offline
      </span>
    );
  }

  if (!data) {
    return (
      <span className="hidden h-8 w-32 skeleton rounded-lg sm:block" />
    );
  }

  const warming = data.status !== "ok";

  return (
    <span
      className={`hidden items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs font-medium sm:flex ${
        warming
          ? "border-warning/30 bg-warning-wash text-warning"
          : "border-hairline bg-surface text-ink-mute"
      }`}
      title={
        warming
          ? "The retrieval engine is still building its index."
          : `${formatCount(data.bookCount)} books indexed · v${data.version}`
      }
    >
      <span
        className={`size-1.5 rounded-full ${warming ? "bg-warning" : "bg-success"}`}
      />
      {warming ? "Waking the engine…" : `${formatCount(data.bookCount)} books`}
    </span>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-hairline bg-ground/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 w-full max-w-[1400px] items-center gap-3 px-4 sm:px-6">
          <Link
            href="/"
            className="flex shrink-0 items-center gap-2.5 rounded-lg py-1 pr-2"
          >
            <Logomark />
            <span className="flex flex-col leading-none">
              <span className="font-display text-[17px] font-semibold tracking-tight text-ink">
                Iqra
              </span>
              <span className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.16em] text-ink-mute">
                Digital Library
              </span>
            </span>
          </Link>

          <nav className="ml-4 hidden items-center gap-0.5 lg:flex">
            {NAV.map(({ href, label, icon: Icon }) => {
              const active =
                href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
                    active
                      ? "bg-brand-wash text-brand"
                      : "text-ink-soft hover:bg-surface-2 hover:text-ink"
                  }`}
                >
                  <Icon className="size-4" />
                  {label}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <EngineStatus />
            <ThemeToggle />
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              className="grid size-9 place-items-center rounded-lg border border-hairline bg-surface text-ink-mute lg:hidden"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
            >
              {menuOpen ? <X className="size-4" /> : <Menu className="size-4" />}
            </button>
          </div>
        </div>

        {menuOpen && (
          <nav className="border-t border-hairline bg-surface px-4 py-2 lg:hidden">
            {NAV.map(({ href, label, icon: Icon }) => {
              const active =
                href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMenuOpen(false)}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${
                    active ? "bg-brand-wash text-brand" : "text-ink-soft"
                  }`}
                >
                  <Icon className="size-4" />
                  {label}
                </Link>
              );
            })}
          </nav>
        )}
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-hairline bg-surface">
        <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-2 px-4 py-6 text-xs text-ink-mute sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>
            Iqra Digital Library — hybrid retrieval, explainable RAG.{" "}
            <span dir="rtl" className="font-display">
              مكتبة إقرأ الرقمية
            </span>
          </p>
          <p className="font-mono text-[11px] uppercase tracking-[0.12em]">
            DiploTech Solutions
          </p>
        </div>
      </footer>
    </div>
  );
}
