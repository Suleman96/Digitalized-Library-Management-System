/**
 * API types.
 *
 * These mirror the Pydantic models in `apps/api/schemas.py`, which are the
 * single source of truth. To regenerate them from the live schema:
 *
 *     npm run gen:types
 *
 * The generated file lands at `lib/api-schema.d.ts`; the hand-written aliases
 * below stay stable so components never import generated paths directly.
 */

export interface Book {
  id: string;
  title: string;
  authors: string;
  subtitle: string;
  description: string;
  thumbnail: string;
  average_rating: number;
  ratings_count: number;
  info_link: string;
  language: string;
  published_year: string;
  num_pages: number;
  source: string;
  similarity: number;
  categories: string;
}

/** One stage of the retrieval pipeline, as it actually ran. */
export interface StageTrace {
  name:
    | "multi_query"
    | "hyde"
    | "hybrid_retrieve"
    | "rrf"
    | "rerank"
    | (string & {});
  candidates: number;
  durationMs: number;
  detail: string;
  topShift: number | null;
}

/**
 * What the engine did to answer a search. Rendering this is the point: without
 * it, the pipeline's work is invisible and a user just sees a list.
 */
export interface PipelineTrace {
  originalQuery: string;
  hydeDocument: string | null;
  queryVariants: string[];
  stages: StageTrace[];
  totalMs: number;
}

export type SearchScope = "both" | "local" | "external";
export type SortBy = "similarity" | "rating" | "year";

export interface SearchRequest {
  query: string;
  language?: string;
  category?: string;
  localLimit?: number;
  externalLimit?: number;
  minRating?: number;
  scope?: SearchScope;
  sortBy?: SortBy;
  useAiExpansion?: boolean;
  useHyde?: boolean;
  useMultiQuery?: boolean;
  useRerank?: boolean;
}

export interface SearchResponse {
  local: Book[];
  external: Book[];
  trace: PipelineTrace;
  expandedQuery: string | null;
}

export interface BookPage {
  items: Book[];
  page: number;
  pageSize: number;
  total: number;
  pageCount: number;
}

export interface MutationResult {
  ok: boolean;
  message: string;
  count: number | null;
}

export interface ProviderInfo {
  provider: string;
  models: string[];
  requiresKey: boolean;
  keyConfigured: boolean;
}

export interface LLMStatus {
  connected: boolean;
  provider: string | null;
  model: string | null;
  message: string;
  capabilities: Record<string, boolean>;
}

export interface AnalyticsSummary {
  totalBooks: number;
  averageRating: number;
  categoryCount: number;
  totalPages: number;
  ratedBooks: number;
  earliestYear: number | null;
  latestYear: number | null;
}

export interface RatingBin {
  label: string;
  midpoint: number;
  count: number;
}

export interface CategoryBin {
  label: string;
  count: number;
}

export interface YearPoint {
  year: number;
  count: number;
}

export interface AnalyticsResponse {
  available: boolean;
  summary: AnalyticsSummary | null;
  ratings: RatingBin[];
  categories: CategoryBin[];
  years: YearPoint[];
}

export interface HealthResponse {
  status: "ok" | "starting" | "degraded";
  indexReady: boolean;
  agentReady: boolean;
  llmConnected: boolean;
  bookCount: number;
  version: string;
}

export interface ExplainResponse {
  explanation: string;
  provider: string | null;
  model: string | null;
}

/** Events emitted by the agent's SSE stream. */
export type AgentEvent =
  | { type: "token"; text: string }
  | { type: "tool_call"; name: string }
  | { type: "tool_result"; name: string; preview: string }
  | { type: "done"; text: string }
  | { type: "error"; message: string };

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  /** Tools the agent chose while producing this reply. */
  steps?: { name: string; preview?: string }[];
}
