"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState } from "react";

import { ApiError } from "@/lib/api";

export function Providers({ children }: { children: React.ReactNode }) {
  // Created in state so the client is stable across re-renders but never
  // shared between users during SSR.
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            refetchOnWindowFocus: false,
            retry: (failureCount, error) => {
              // A cold Space returns 503 while it builds its index — that one
              // is genuinely worth waiting out. Nothing else is.
              if (error instanceof ApiError && error.isStarting) {
                return failureCount < 8;
              }
              return failureCount < 1;
            },
            retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}
