export const API = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "production" ? "/api" : "http://127.0.0.1:8000/api");
const LOCAL_REACTIONS = process.env.NEXT_PUBLIC_LOCAL_REACTIONS === "1";

function requestUrl(path: string) {
  return LOCAL_REACTIONS && /^\/articles\/\d+\/reactions(?:\/collect)?$/.test(path)
    ? `/local-reactions${path}`
    : `${API}${path}`;
}

export type CountLabel = { label: string; count: number };
export type Overview = {
  total_articles: number;
  relevant_articles: number;
  story_clusters: number;
  sources: number;
  languages: number;
  topics_detected: number;
  synthetic_articles: number;
  by_language: CountLabel[];
  by_source: CountLabel[];
  sentiment_distribution: CountLabel[];
  topic_distribution: CountLabel[];
  articles_over_time: { date: string; count: number }[];
};
export type AnalysisProviderStatus = {
  provider: string;
  display_name: string;
  model: string | null;
  ready: boolean;
  api_key_configured: boolean;
  synthetic_records_use_local: boolean;
  message: string;
  text_generation?: {
    provider: string;
    display_name: string;
    model: string;
    ready: boolean;
    api_key_configured: boolean;
    synthetic_records_use_local: boolean;
  };
};
export type StoryCard = {
  id: number;
  canonical_title: string;
  summary: string;
  article_count: number;
  languages: string[];
  sources: string[];
  first_seen: string | null;
  last_updated: string | null;
  goi_relevance: number;
  is_synthetic: boolean;
  is_manually_curated: boolean;
};
export type SourceRecord = {
  id: number;
  name: string;
  domain: string | null;
  language: string;
  region: string | null;
  source_type: string;
  rss_url: string | null;
  is_active: boolean;
  article_count: number;
};
export type ArticleCard = {
  id: number;
  title: string;
  url: string;
  source: { id: number; name: string; domain: string | null };
  published_at: string | null;
  language: string;
  language_confidence: number;
  region: string | null;
  is_synthetic: boolean;
  collection_method: string;
  content_kind: string;
  search_query: string | null;
  discovery_url: string | null;
  research_job_id: number | null;
  goi_relevance: number;
  sentiment: string;
  topics: { topic: string; confidence: number; evidence: string }[];
  summary: string;
};
export type PublicReaction = {
  id: number;
  platform: "bluesky" | "hacker_news";
  text: string;
  url: string;
  published_at: string | null;
  discussion_title: string | null;
  engagement_label: "likes" | "points";
  likes: number;
  replies: number;
  reposts: number;
  match_basis: "article_link" | "headline_terms";
  sentiment: "positive" | "negative" | "mixed" | "neutral" | "uncertain";
  confidence: number;
};
export type PublicReactionReport = {
  available: boolean;
  article_id: number;
  id?: number;
  status?: "complete" | "no_results" | "analysis_unavailable";
  query?: string;
  sample_count?: number;
  distribution?: Record<"positive" | "negative" | "mixed" | "neutral" | "uncertain", number>;
  summary?: string;
  themes?: { label: string; evidence: string[] }[];
  classifier?: string | null;
  summarizer?: string | null;
  sources?: { platform: "bluesky" | "hacker_news"; label: string; status: "collected" | "no_matches" | "unavailable"; count: number; note: string }[];
  notes?: string[];
  reactions?: PublicReaction[];
  collected_at?: string | null;
  cache_hit?: boolean;
};
export type StoryDetail = StoryCard & {
  articles: ArticleCard[];
  comparison: {
    interpretation_note: string;
    shared_narrative: {
      topics: { topic: string; article_ids: number[]; sample_count: number }[];
      entities: { entity: string; article_ids: number[]; sample_count: number }[];
    };
    language_comparison: {
      language: string;
      sample_size: number;
      sources: string[];
      sentiment_distribution: Record<string, number>;
      main_topics: { topic: string; count: number }[];
      article_ids: number[];
    }[];
    source_comparison: {
      source: string;
      language: string;
      sample_size: number;
      sentiment_distribution: Record<string, number>;
      main_topics: { topic: string; count: number }[];
      article_ids: number[];
    }[];
    coverage_differences: {
      dimension: string;
      group_a: string;
      group_b: string;
      difference: string;
      sample_sizes: Record<string, number>;
      article_ids: number[];
    }[];
  };
};

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(requestUrl(path), { cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || `API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

async function apiWrite<T>(path: string, method: "POST" | "PUT" | "PATCH" | "DELETE", body?: unknown): Promise<T> {
  const response = await fetch(requestUrl(path), {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    throw new Error(typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((item) => item.msg).join("; ") : `API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const apiPost = <T>(path: string, body?: unknown) => apiWrite<T>(path, "POST", body);
export const apiPut = <T>(path: string, body: unknown) => apiWrite<T>(path, "PUT", body);
export const apiPatch = <T>(path: string, body: unknown) => apiWrite<T>(path, "PATCH", body);
export const apiDelete = <T>(path: string) => apiWrite<T>(path, "DELETE");

export type ResearchOptions = {
  languages: { code: string; label: string }[];
  outlets: { id: string; name: string; domains: string[] }[];
  default_from_date: string;
  default_to_date: string;
  providers: string[];
  requires_api_key: boolean;
  maximum_date_range_days: number;
  maximum_articles_per_language: number;
};

export type ResearchJob = {
  id: number;
  job_type: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  metadata: {
    request?: { query: string; aliases: string[]; from_date: string; to_date: string; languages: string[]; outlet_ids: string[]; per_language_limit: number };
    phase?: string;
    result?: {
      created: number;
      duplicates: number;
      failed: number;
      article_ids: number[];
      story_ids: number[];
      stories_created: number;
      articles_processed: number;
      full_text_count: number;
      excerpt_count: number;
      provider_counts: Record<string, number>;
      warnings: string[];
      embedding_model: string;
    };
  };
};

export const LANGUAGE_LABELS: Record<string, string> = {
  en: "English", hi: "Hindi", kn: "Kannada", ta: "Tamil", te: "Telugu", und: "Unclear",
};

export function languageName(code: string) {
  return LANGUAGE_LABELS[code] || code.toUpperCase();
}

export function formatDate(value: string | null | undefined) {
  if (!value) return "Date not supplied";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Date not supplied" : new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(date);
}
