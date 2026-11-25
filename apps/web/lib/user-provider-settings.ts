export type UserProviderSettings = {
  geminiModel: string;
  geminiApiKey: string;
  scrapeCreatorsApiKey: string;
};

const STORAGE_KEY = "prj277-provider-settings-v1";
const DEFAULT_MODEL = "gemini-3.8-flash";

export function readUserProviderSettings(): UserProviderSettings {
  const fallback = { geminiModel: DEFAULT_MODEL, geminiApiKey: "", scrapeCreatorsApiKey: "" };
  if (typeof window === "undefined") return fallback;
  try {
    const saved = window.sessionStorage.getItem(STORAGE_KEY);
    if (!saved) return fallback;
    const value = JSON.parse(saved) as Partial<UserProviderSettings>;
    return {
      geminiModel: typeof value.geminiModel === "string" ? value.geminiModel : DEFAULT_MODEL,
      geminiApiKey: typeof value.geminiApiKey === "string" ? value.geminiApiKey : "",
      scrapeCreatorsApiKey: typeof value.scrapeCreatorsApiKey === "string" ? value.scrapeCreatorsApiKey : "",
    };
  } catch {
    return fallback;
  }
}

export function writeUserProviderSettings(settings: UserProviderSettings): boolean {
  if (typeof window === "undefined") return false;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    return true;
  } catch {
    return false;
  }
}

export function headersForProviderRequest(path: string): Record<string, string> {
  const settings = readUserProviderSettings();
  const normalizedPath = path.split("?")[0];
  const isReactionCollection = /^\/?articles\/\d+\/reactions\/collect$/.test(normalizedPath)
    || /^\/?local-reactions\/articles\/\d+\/reactions\/collect$/.test(normalizedPath);
  const isAnalysisRequest = /^\/?articles\/\d+\/analyze$/.test(normalizedPath)
    || ["/research/search", "/ingestion/url", "/ingestion/rss", "/ingestion/dataset"].includes(`/${normalizedPath.replace(/^\//, "")}`);
  const headers: Record<string, string> = {};
  if (isAnalysisRequest && settings.geminiApiKey) {
    headers["x-prj277-gemini-key"] = settings.geminiApiKey;
    headers["x-prj277-gemini-model"] = settings.geminiModel;
  }
  if (isReactionCollection) {
    if (settings.geminiApiKey) headers["x-prj277-gemini-key"] = settings.geminiApiKey;
    if (settings.geminiModel) headers["x-prj277-gemini-model"] = settings.geminiModel;
    if (settings.scrapeCreatorsApiKey) headers["x-prj277-scrapecreators-key"] = settings.scrapeCreatorsApiKey;
  }
  return headers;
}
