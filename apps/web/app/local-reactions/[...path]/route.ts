import { collectAndAnalyzePublicReactions, type PublicReactionResult, type ReactionEnvironment } from "@/lib/public-reactions";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type LocalReport = PublicReactionResult & {
  available: true;
  article_id: number;
  collected_at: string;
  reactions: (PublicReactionResult["reactions"][number] & { id: number })[];
  cache_hit?: boolean;
};

type CachedReport = { createdAt: number; report: LocalReport };
const globalCache = globalThis as typeof globalThis & { __prj277LocalReactionCache?: Map<number, CachedReport> };
const reports = globalCache.__prj277LocalReactionCache ??= new Map<number, CachedReport>();
const cacheLifetime = 5 * 60 * 1000;
const apiBase = process.env.LOCAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

async function dispatch(request: Request, context: { params: Promise<{ path: string[] }> }) {
  if (process.env.NEXT_PUBLIC_LOCAL_REACTIONS !== "1") {
    return Response.json({ detail: "Not found" }, { status: 404 });
  }

  const { path } = await context.params;
  const isReportPath = path.length === 3 && path[0] === "articles" && path[2] === "reactions";
  const isCollectPath = path.length === 4 && path[0] === "articles" && path[2] === "reactions" && path[3] === "collect";
  const articleId = Number(path[1]);
  if ((!isReportPath && !isCollectPath) || !Number.isSafeInteger(articleId) || articleId < 1) {
    return Response.json({ detail: "Not found" }, { status: 404 });
  }

  const cached = reports.get(articleId);
  if (request.method === "GET" && isReportPath) {
    if (cached && Date.now() - cached.createdAt < cacheLifetime) {
      return Response.json({ ...cached.report, cache_hit: false });
    }
    if (cached) reports.delete(articleId);
    return Response.json({ available: false, article_id: articleId });
  }

  if (request.method !== "POST" || !isCollectPath) {
    return Response.json({ detail: "Method not allowed" }, { status: 405 });
  }
  if (cached && Date.now() - cached.createdAt < cacheLifetime) {
    return Response.json({ ...cached.report, cache_hit: true });
  }
  if (cached) reports.delete(articleId);

  let articleResponse: Response;
  try {
    articleResponse = await fetch(`${apiBase}/articles/${articleId}`, { cache: "no-store", signal: AbortSignal.timeout(8000) });
  } catch {
    return Response.json({ detail: "The local article service is unavailable." }, { status: 502 });
  }
  const article = await articleResponse.json().catch(() => null) as {
    id?: number; title?: string; url?: string; is_synthetic?: boolean; detail?: string;
  } | null;
  if (!articleResponse.ok) {
    return Response.json({ detail: article?.detail || "Article could not be loaded." }, { status: articleResponse.status });
  }
  if (article?.is_synthetic) {
    return Response.json({ detail: "Public reactions are available only for collected real articles." }, { status: 409 });
  }
  if (!article?.title || !article.url) {
    return Response.json({ detail: "The article is missing a title or source URL." }, { status: 422 });
  }

  const env: ReactionEnvironment = {
    TYPESAFE_API_KEY: process.env.TYPESAFE_API_KEY,
    TYPESAFE_MODEL: process.env.TYPESAFE_MODEL,
    JEV_MIN_CONFIDENCE: process.env.JEV_MIN_CONFIDENCE,
    GEMINI_API_KEY: process.env.GEMINI_API_KEY,
    GEMINI_MODEL: process.env.GEMINI_MODEL,
  };
  const result = await collectAndAnalyzePublicReactions({ title: article.title, url: article.url }, env);
  const report: LocalReport = {
    ...result,
    available: true,
    article_id: articleId,
    collected_at: new Date().toISOString(),
    reactions: result.reactions.map((reaction, index) => ({ ...reaction, id: index + 1 })),
  };
  reports.set(articleId, { createdAt: Date.now(), report });
  return Response.json(report);
}

export const GET = dispatch;
export const POST = dispatch;
