/**
 * Typed client for the Iqra API.
 *
 * Every network call in the app goes through here. Components never build URLs
 * or call fetch directly, so error handling, base-URL resolution, and the
 * request shape all live in exactly one place.
 */

import type {
  AnalyticsResponse,
  Book,
  BookPage,
  ExplainResponse,
  HealthResponse,
  LLMStatus,
  MutationResult,
  ProviderInfo,
  SearchRequest,
  SearchResponse,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

/** An API error carrying the status code, so callers can branch on it. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** The engine is still building its index. Worth retrying. */
  get isStarting() {
    return this.status === 503;
  }

  /** An AI provider is required but not connected. */
  get needsProvider() {
    return this.status === 409;
  }

  get isRateLimited() {
    return this.status === 429;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    // fetch only rejects on network failure, so this is unambiguous.
    throw new ApiError(
      0,
      `Cannot reach the API at ${API_BASE}. Is it running? Start it with: uvicorn apps.api.main:app --port 8000`,
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail)) {
        // FastAPI validation errors arrive as a list of field errors.
        detail = body.detail
          .map((e: { loc?: string[]; msg?: string }) =>
            e.loc ? `${e.loc.slice(1).join(".")}: ${e.msg}` : e.msg,
          )
          .join("; ");
      }
    } catch {
      /* response had no JSON body; statusText stands */
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });

const del = <T>(path: string) => request<T>(path, { method: "DELETE" });

// ---------------------------------------------------------------------------

export const api = {
  health: () => request<HealthResponse>("/api/health"),

  search: (body: SearchRequest) => post<SearchResponse>("/api/search", body),

  explain: (query: string, bookId: string) =>
    post<ExplainResponse>("/api/explain", { query, bookId }),

  books: {
    browse: (params: {
      q?: string;
      page?: number;
      pageSize?: number;
      language?: string;
      minRating?: number;
    }) => {
      const search = new URLSearchParams();
      if (params.q) search.set("q", params.q);
      if (params.page) search.set("page", String(params.page));
      if (params.pageSize) search.set("pageSize", String(params.pageSize));
      if (params.language) search.set("language", params.language);
      if (params.minRating) search.set("minRating", String(params.minRating));
      return request<BookPage>(`/api/books?${search}`);
    },
    get: (id: string) => request<Book>(`/api/books/${id}`),
    similar: (id: string, limit = 6) =>
      request<Book[]>(`/api/books/${id}/similar?limit=${limit}`),
    add: (book: Record<string, unknown>) => post<MutationResult>("/api/books", book),
    remove: (id: string) => del<MutationResult>(`/api/books/${id}`),
  },

  readingList: {
    all: () => request<Book[]>("/api/reading-list"),
    save: (book: Book) => post<MutationResult>("/api/reading-list", { book }),
    remove: (id: string) => del<MutationResult>(`/api/reading-list/${id}`),
    clear: () => del<void>("/api/reading-list"),
    exportUrl: () => `${API_BASE}/api/reading-list/export`,
  },

  analytics: () => request<AnalyticsResponse>("/api/analytics"),

  llm: {
    providers: () => request<ProviderInfo[]>("/api/llm/providers"),
    status: () => request<LLMStatus>("/api/llm/status"),
    connect: (body: {
      provider: string;
      model: string;
      ollamaHost?: string;
      apiKey?: string;
    }) => post<LLMStatus>("/api/llm/connect", body),
  },

  agent: {
    chatUrl: () => `${API_BASE}/api/agent/chat`,
    clearThread: (id: string) => del<void>(`/api/agent/thread/${id}`),
  },
};
