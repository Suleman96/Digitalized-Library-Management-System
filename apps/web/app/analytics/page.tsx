"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api } from "@/lib/api";
import { formatCount } from "@/lib/format";

/** Reads the live CSS tokens so charts follow the active theme. */
function useChartColors() {
  const [colors, setColors] = useState({
    brand: "#165491",
    ink: "#12181f",
    mute: "#66788c",
    hairline: "#dce3ec",
    surface: "#ffffff",
    warning: "#8a5a05",
  });

  useEffect(() => {
    const read = () => {
      const s = getComputedStyle(document.documentElement);
      setColors({
        brand: s.getPropertyValue("--brand").trim() || "#165491",
        ink: s.getPropertyValue("--ink").trim() || "#12181f",
        mute: s.getPropertyValue("--ink-mute").trim() || "#66788c",
        hairline: s.getPropertyValue("--hairline").trim() || "#dce3ec",
        surface: s.getPropertyValue("--surface").trim() || "#ffffff",
        warning: s.getPropertyValue("--warning").trim() || "#8a5a05",
      });
    };
    read();
    const observer = new MutationObserver(read);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, []);

  return colors;
}

export default function AnalyticsPage() {
  const c = useChartColors();
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["analytics"],
    queryFn: api.analytics,
  });

  const tooltipStyle = {
    background: c.surface,
    border: `1px solid ${c.hairline}`,
    borderRadius: 8,
    fontSize: 12,
    color: c.ink,
  };

  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 py-8 sm:px-6">
      <header className="mb-6">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
          What is in the collection
        </h1>
        <p className="mt-1.5 max-w-2xl text-[14px] leading-relaxed text-ink-soft">
          A profile of the catalogue itself — how books are rated, what subjects
          dominate, and when they were published.
        </p>
      </header>

      {isError && (
        <p className="rounded-xl border border-danger/30 bg-danger-wash p-4 text-[13px] text-danger">
          {(error as Error).message}
        </p>
      )}

      {isPending && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-xl" />
          ))}
        </div>
      )}

      {data?.summary && (
        <>
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Books" value={formatCount(data.summary.totalBooks)} />
            <Stat
              label="Average rating"
              value={data.summary.averageRating.toFixed(2)}
              hint="out of 5"
            />
            <Stat
              label="Subjects"
              value={formatCount(data.summary.categoryCount)}
            />
            <Stat
              label="Pages in total"
              value={formatCount(data.summary.totalPages)}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel
              title="How books are rated"
              caption="Most books cluster around 3.5–4.5. The tails are where the surprises live."
            >
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.ratings}>
                  <CartesianGrid vertical={false} stroke={c.hairline} />
                  <XAxis
                    dataKey="midpoint"
                    stroke={c.mute}
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: c.hairline }}
                  />
                  <YAxis
                    stroke={c.mute}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    width={40}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    cursor={{ fill: c.hairline, opacity: 0.3 }}
                    formatter={(v) => [formatCount(Number(v ?? 0)), "books"]}
                    labelFormatter={(l) => `Rating ≈ ${l}`}
                  />
                  <Bar
                    dataKey="count"
                    fill={c.brand}
                    radius={[3, 3, 0, 0]}
                    isAnimationActive={false}
                  />
                </BarChart>
              </ResponsiveContainer>
            </Panel>

            <Panel
              title="The biggest subjects"
              caption="The twelve most common categories across the collection."
            >
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.categories} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid horizontal={false} stroke={c.hairline} />
                  <XAxis
                    type="number"
                    stroke={c.mute}
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: c.hairline }}
                  />
                  <YAxis
                    type="category"
                    dataKey="label"
                    stroke={c.mute}
                    fontSize={10}
                    tickLine={false}
                    axisLine={false}
                    width={150}
                    interval={0}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    cursor={{ fill: c.hairline, opacity: 0.3 }}
                    formatter={(v) => [formatCount(Number(v ?? 0)), "books"]}
                  />
                  <Bar dataKey="count" radius={[0, 3, 3, 0]} isAnimationActive={false}>
                    {data.categories.map((_, i) => (
                      <Cell key={i} fill={i === 0 ? c.brand : `${c.brand}99`} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Panel>

            <Panel
              title="When they were published"
              caption={
                data.summary.earliestYear
                  ? `Spanning ${data.summary.earliestYear} to ${data.summary.latestYear}.`
                  : "Publication years across the collection."
              }
              wide
            >
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={data.years}>
                  <defs>
                    <linearGradient id="yearFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={c.brand} stopOpacity={0.28} />
                      <stop offset="100%" stopColor={c.brand} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke={c.hairline} />
                  <XAxis
                    dataKey="year"
                    stroke={c.mute}
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: c.hairline }}
                    interval={11}
                  />
                  <YAxis
                    stroke={c.mute}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    width={40}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(v) => [formatCount(Number(v ?? 0)), "books"]}
                    labelFormatter={(l) => `Published in ${l}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke={c.brand}
                    strokeWidth={2}
                    fill="url(#yearFill)"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-hairline bg-surface p-4 shadow-card">
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute">
        {label}
      </p>
      <p className="tnum mt-2 font-display text-3xl font-semibold text-ink">
        {value}
        {hint && (
          <span className="ml-1.5 font-sans text-[12px] font-normal text-ink-mute">
            {hint}
          </span>
        )}
      </p>
    </div>
  );
}

function Panel({
  title,
  caption,
  wide,
  children,
}: {
  title: string;
  caption: string;
  wide?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section
      className={`rounded-xl border border-hairline bg-surface p-4 shadow-card ${
        wide ? "lg:col-span-2" : ""
      }`}
    >
      <h2 className="font-display text-lg font-semibold text-ink">{title}</h2>
      <p className="mt-0.5 mb-4 text-[12px] text-ink-mute">{caption}</p>
      {children}
    </section>
  );
}
