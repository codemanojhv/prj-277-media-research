"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ArrowUpRight, Search, Sparkles } from "lucide-react";
import { apiGet, apiPost, formatDate, languageName, type ArticleCard, type SourceRecord, type StoryCard } from "@/lib/api";

type SearchPayload = { query: string; count: number; score_mode: string; items: { score: number; article: ArticleCard }[] };
type Choice = { label: string; value: string };
type ResearchJobChoice = { id: number; status: string; metadata: { request?: { query?: string } } };

export default function CorpusSearchPage() {
  const hosted = process.env.NEXT_PUBLIC_DEPLOYMENT_LABEL?.includes("CLOUDFLARE") || false;
  const [query, setQuery] = useState("");
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [languages, setLanguages] = useState<Choice[]>([]);
  const [topics, setTopics] = useState<Choice[]>([]);
  const [stories, setStories] = useState<StoryCard[]>([]);
  const [researchJobs, setResearchJobs] = useState<ResearchJobChoice[]>([]);
  const [results, setResults] = useState<SearchPayload | null>(null);
  const [filters, setFilters] = useState({ language: "", source_id: "", from_date: "", to_date: "", region: "", sentiment: "", topic: "", is_goi_relevant: "", is_synthetic: "", story_id: "", research_job_id: "" });
  const [targetStory, setTargetStory] = useState("");
  const [loading, setLoading] = useState(false);
  const [assigning, setAssigning] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet<{ items: SourceRecord[] }>("/sources"),
      apiGet<{ items: { language: string; count: number }[] }>("/languages"),
      apiGet<{ items: { topic: string; count: number }[] }>("/topics"),
      apiGet<{ items: StoryCard[] }>("/stories?limit=200"),
      apiGet<{ items: ResearchJobChoice[] }>("/research/jobs?limit=50"),
    ]).then(([sourceData, languageData, topicData, storyData, jobData]) => {
      setSources(sourceData.items);
      setLanguages(languageData.items.map((item) => ({ label: languageName(item.language), value: item.language })));
      setTopics(topicData.items.map((item) => ({ label: `${item.topic} · ${item.count}`, value: item.topic })));
      setStories(storyData.items);
      setResearchJobs(jobData.items);
    }).catch((issue) => setError(issue.message));
  }, []);

  async function runSearch(event: FormEvent) {
    event.preventDefault();
    if (query.trim().length < 2) {
      setError("Enter at least two characters to search the corpus.");
      return;
    }
    const params = new URLSearchParams({ q: query.trim(), limit: "50" });
    for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
    setLoading(true);
    setError("");
    setMessage("");
    try { setResults(await apiGet<SearchPayload>(`/search?${params}`)); }
    catch (issue) { setError(issue instanceof Error ? issue.message : "Search failed."); }
    finally { setLoading(false); }
  }

  async function assign(articleId: number) {
    if (!targetStory) return;
    setAssigning(articleId);
    setMessage("");
    setError("");
    try {
      await apiPost(`/stories/${targetStory}/articles`, { article_id: articleId });
      setMessage(`Article ${articleId} is now assigned to the selected story. The cluster will be preserved during reprocessing.`);
      setStories((items) => items.map((story) => story.id === Number(targetStory) ? { ...story, is_manually_curated: true } : story));
    } catch (issue) { setError(issue instanceof Error ? issue.message : "Article could not be assigned."); }
    finally { setAssigning(null); }
  }

  function setFilter(name: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  return <>
    <div className="page-heading-row"><div><p className="eyebrow">{hosted ? "STORED SAMPLE / KEYWORD SEARCH" : "CROSS-INDEX / STORED ARTICLE VECTORS"}</p><h1 className="page-title">Explore the corpus</h1><p className="page-lede">{hosted ? "Rank stored articles by keyword overlap, then narrow the sample with research filters." : "Search across every stored article using its saved multilingual representation, then narrow the sample with research filters."}</p></div><div className="heading-meta"><strong>{results?.count.toLocaleString() || "—"} MATCHES</strong>Filtered corpus results</div></div>
    <div className="explore-layout">
      <form className="panel explore-filters" onSubmit={runSearch}>
        <label className="field-label" htmlFor="corpus-query">Search question or phrase</label>
        <div className="explore-query"><input id="corpus-query" className="research-text-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. solar access in rural communities" /><button className="btn-primary" type="submit" disabled={loading}><Search size={14} />{loading ? "Searching…" : "Search"}</button></div>
        <div className="explore-filter-grid">
          <label className="field-label">Language<select className="filter-select" value={filters.language} onChange={(event) => setFilter("language", event.target.value)}><option value="">Any language</option>{languages.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label className="field-label">Source<select className="filter-select" value={filters.source_id} onChange={(event) => setFilter("source_id", event.target.value)}><option value="">Any source</option>{sources.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label className="field-label">From<input className="filter-input" type="date" value={filters.from_date} onChange={(event) => setFilter("from_date", event.target.value)} /></label>
          <label className="field-label">To<input className="filter-input" type="date" value={filters.to_date} onChange={(event) => setFilter("to_date", event.target.value)} /></label>
          <label className="field-label">Region<input className="filter-input" value={filters.region} onChange={(event) => setFilter("region", event.target.value)} placeholder="Any region" /></label>
          <label className="field-label">Topic<select className="filter-select" value={filters.topic} onChange={(event) => setFilter("topic", event.target.value)}><option value="">Any topic</option>{topics.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label className="field-label">Sentiment<select className="filter-select" value={filters.sentiment} onChange={(event) => setFilter("sentiment", event.target.value)}><option value="">Any sentiment</option>{["positive", "negative", "mixed", "neutral", "uncertain"].map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="field-label">Central government relevance<select className="filter-select" value={filters.is_goi_relevant} onChange={(event) => setFilter("is_goi_relevant", event.target.value)}><option value="">Any result</option><option value="true">Relevant</option><option value="false">Not marked relevant</option></select></label>
          <label className="field-label">Record type<select className="filter-select" value={filters.is_synthetic} onChange={(event) => setFilter("is_synthetic", event.target.value)}><option value="">All records</option><option value="false">Collected or imported</option><option value="true">Synthetic classroom data</option></select></label>
          <label className="field-label">Story group<select className="filter-select" value={filters.story_id} onChange={(event) => setFilter("story_id", event.target.value)}><option value="">Any story</option>{stories.map((story) => <option value={story.id} key={story.id}>#{story.id} · {story.canonical_title.replace(/^\[SYNTHETIC\]\s*/i, "")}</option>)}</select></label>
          <label className="field-label">Research run<select className="filter-select" value={filters.research_job_id} onChange={(event) => setFilter("research_job_id", event.target.value)}><option value="">All research runs</option>{researchJobs.map((job) => <option value={job.id} key={job.id}>#{job.id} · {job.metadata.request?.query || "Topic search"} · {job.status}</option>)}</select></label>
        </div>
        {!hosted && <div className="assignment-control"><label className="field-label" htmlFor="target-story">Curate a result into a story</label><div><select id="target-story" className="filter-select" value={targetStory} onChange={(event) => setTargetStory(event.target.value)}><option value="">Choose a story</option>{stories.map((story) => <option key={story.id} value={story.id}>{story.canonical_title.replace(/^\[SYNTHETIC\]\s*/i, "")}</option>)}</select><span>This saves a manual cluster correction.</span></div></div>}
      </form>
      <section className="explore-results">
        {error && <div className="error-state" role="alert">{error}</div>}
        {message && <div className="success-state" role="status">{message}</div>}
        {results && <div className="results-caption"><span><Sparkles size={13} /> Ranked with {hosted ? "keyword overlap on the hosted store" : results.score_mode === "semantic" ? "the stored embedding model" : results.score_mode === "lexical-fallback" ? "a lexical fallback because the embedding model is unavailable" : "the available search mode"}.</span><b>{results.count} matches</b></div>}
        {!results && !loading ? <div className="panel explore-empty"><Search size={24} /><h2>Search the stored sample</h2><p>Results include the source, detected language, analysis labels, and a link to inspect full article evidence.</p></div> : null}
        {loading && <div className="loading-state">Searching stored article representations…</div>}
        {results && results.items.length === 0 && <div className="empty-state">No matching articles were found for this query and filter set.</div>}
        {results?.items.map(({ score, article }, index) => <article className="panel explore-result" key={article.id}>
          <div className="explore-result-top"><span className="eyebrow">MATCH {String(index + 1).padStart(2, "0")} · SCORE {score.toFixed(3)}</span><span className={article.is_synthetic ? "synthetic-pill" : "content-kind full"}>{article.is_synthetic ? "Synthetic" : article.content_kind === "feed_excerpt" ? "Feed excerpt" : "Stored article"}</span></div>
          <Link className="explore-result-title" href={`/articles/${article.id}`}>{article.title.replace(/^\[SYNTHETIC\]\s*/i, "")}<ArrowUpRight size={14} /></Link>
          <p>{article.summary}</p>
          <div className="explore-result-meta"><span>{article.source.name}</span><span>{languageName(article.language)}</span><span>{formatDate(article.published_at)}</span><span>Article tone: {article.sentiment}</span></div>
          <div className="explore-result-foot"><span>{article.topics.slice(0, 3).map((item) => item.topic).join(" · ") || "No topic labels"}</span>{!hosted && <button className="btn-secondary" type="button" disabled={!targetStory || assigning === article.id} onClick={() => void assign(article.id)}>{assigning === article.id ? "Saving…" : "Assign to story"}</button>}</div>
        </article>)}
      </section>
    </div>
    <p className="page-footer-note">Similarity is a retrieval aid, not proof that two articles report the same event. Check source text, dates, and language before interpreting the result.</p>
  </>;
}
