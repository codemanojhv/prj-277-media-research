"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, FileText, Layers3, Languages, RefreshCw, Search, ShieldCheck, Workflow } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { API, apiGet, languageName, type AnalysisProviderStatus, type Overview, type StoryCard } from "@/lib/api";

type SelectItem = { id: number; name: string; language: string; region: string | null };

export default function DashboardPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [providerStatus, setProviderStatus] = useState<AnalysisProviderStatus | null>(null);
  const [stories, setStories] = useState<StoryCard[]>([]);
  const [sources, setSources] = useState<SelectItem[]>([]);
  const [language, setLanguage] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet<Overview>("/analytics/overview"),
      apiGet<{ items: SelectItem[] }>("/sources"),
    ]).then(([summary, sourceList]) => {
      setOverview(summary);
      setSources(sourceList.items);
    }).catch((issue) => setError(issue.message));
  }, []);

  useEffect(() => {
    apiGet<AnalysisProviderStatus>("/analysis/provider").then(setProviderStatus).catch(() => undefined);
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (language) params.set("language", language);
    if (sourceId) params.set("source_id", sourceId);
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);
    apiGet<{ items: StoryCard[] }>(`/stories?${params.toString()}`)
      .then((payload) => { setStories(payload.items); setError(""); })
      .catch((issue) => setError(issue.message))
      .finally(() => setLoading(false));
  }, [language, sourceId, fromDate, toDate]);

  const maxSource = useMemo(() => Math.max(1, ...(overview?.by_source.map((row) => row.count) || [])), [overview]);

  return (
    <>
      <div className="page-heading-row">
        <div>
          <p className="eyebrow">REGIONAL MEDIA / GOVERNMENT COVERAGE</p>
          <h1 className="page-title">Coverage, in context.</h1>
          <p className="page-lede">A 360-degree view of how the same public story appears across languages and outlets. Every signal stays connected to its source article.</p>
        </div>
        <div className="heading-meta"><strong>RESEARCH VIEW / 01</strong>Descriptive measures · article-linked evidence</div>
      </div>

      <div className="demo-banner">
        <div className="demo-seal">i</div>
        <div><strong>SYNTHETIC ACADEMIC DATASET INCLUDED</strong><span>{overview?.synthetic_articles ?? 0} fictional articles for interface demonstration. Online search results are stored with their own query and source provenance.</span></div>
      </div>

      <div className="research-cta-banner"><div><span className="research-cta-icon"><Search size={15} /></span><div><strong>Research a current campaign or announcement</strong><span>Choose a topic, dates, languages, and outlets to collect live public coverage.</span></div></div><Link href="/research" className="btn-primary">Search news coverage <ArrowUpRight size={13} /></Link></div>

      {providerStatus && <div className="note-box" role={providerStatus.ready ? "status" : "alert"}><strong>Structured decisions · {providerStatus.display_name}</strong><br />{providerStatus.message}{providerStatus.text_generation && <><br /><strong>Text generation · {providerStatus.text_generation.display_name}</strong> · {providerStatus.text_generation.model}</>}</div>}

      {error && <div className="error-state" role="alert">{error}. Start the local demo with <code>npm run demo</code> and refresh this page.</div>}

      <section className="metrics-grid" aria-label="Dataset metrics">
        <Metric label="Articles collected" value={overview?.total_articles} foot="STORED RECORDS" icon={<FileText size={16} />} />
        <Metric label="GoI relevant" value={overview?.relevant_articles} foot="STORED CLASSIFICATIONS" icon={<ShieldCheck size={16} />} />
        <Metric label="Story clusters" value={overview?.story_clusters} foot="SEMANTIC GROUPS" icon={<Layers3 size={16} />} />
        <Metric label="Languages" value={overview?.languages} foot="DETECTED IN SAMPLE" icon={<Languages size={16} />} />
      </section>

      <section className="dashboard-grid">
        <div className="panel">
          <div className="panel-header"><div><h2 className="panel-title">Coverage rhythm</h2><p className="panel-subtitle">Published articles by date in the stored sample</p></div><span className="panel-kicker">ARTICLE COUNT</span></div>
          <div className="chart-wrap">
            {overview && overview.articles_over_time.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={overview.articles_over_time} margin={{ top: 15, right: 8, bottom: 0, left: -19 }}>
              <defs><linearGradient id="coverageFade" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#6e9880" stopOpacity={0.25} /><stop offset="90%" stopColor="#6e9880" stopOpacity={0.01} /></linearGradient></defs>
              <CartesianGrid vertical={false} stroke="#ebeae2" strokeDasharray="3 5" />
              <XAxis dataKey="date" tickFormatter={(value: string) => value.slice(5)} tickLine={false} axisLine={false} tick={{ fill: "#92988f", fontSize: 9 }} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "#92988f", fontSize: 9 }} />
              <Tooltip contentStyle={{ border: "1px solid #deddd4", borderRadius: 7, background: "#fbfaf7", fontSize: 10 }} labelStyle={{ color: "#5c695f" }} />
              <Area type="monotone" dataKey="count" stroke="#527a64" strokeWidth={2} fill="url(#coverageFade)" activeDot={{ r: 4, fill: "#cd7654", stroke: "#fbfaf7", strokeWidth: 2 }} />
            </AreaChart></ResponsiveContainer> : <div className="empty-state">Article dates will appear when the dataset is processed.</div>}
          </div>
        </div>
        <div className="panel">
          <div className="panel-header"><div><h2 className="panel-title">By language</h2><p className="panel-subtitle">Counts from stored article records</p></div><span className="panel-kicker">N = {overview?.total_articles ?? 0}</span></div>
          <div className="chart-wrap" style={{ paddingLeft: 4 }}>
            {overview && overview.by_language.length ? <ResponsiveContainer width="100%" height="100%"><BarChart layout="vertical" data={overview.by_language.map((row) => ({ ...row, label: languageName(row.label) }))} margin={{ top: 2, right: 10, bottom: 0, left: 2 }}>
              <CartesianGrid horizontal={false} stroke="#ebeae2" strokeDasharray="3 5" />
              <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "#92988f", fontSize: 9 }} />
              <YAxis type="category" dataKey="label" tickLine={false} axisLine={false} width={75} tick={{ fill: "#6d786f", fontSize: 9 }} />
              <Tooltip cursor={{ fill: "#eef0e9" }} contentStyle={{ border: "1px solid #deddd4", borderRadius: 7, background: "#fbfaf7", fontSize: 10 }} />
              <Bar dataKey="count" fill="#78947e" radius={[0, 4, 4, 0]} barSize={13} />
            </BarChart></ResponsiveContainer> : <div className="empty-state">No language records yet.</div>}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header"><div><h2 className="panel-title">Source sample</h2><p className="panel-subtitle">Outlet counts are descriptive; they do not indicate quality or bias</p></div><span className="panel-kicker">{overview?.sources ?? 0} SOURCES</span></div>
        <div className="source-bars">
          {(overview?.by_source || []).slice(0, 5).map((source) => <div className="source-bar-row" key={source.label}><span>{source.label}</span><strong>{source.count}</strong><div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max(3, source.count / maxSource * 100)}%` }} /></div></div>)}
          {!overview?.by_source.length && <div className="empty-state">Source counts will appear when the dataset is loaded.</div>}
        </div>
      </section>

      <section>
        <div className="section-head"><div><h2>Stories in the sample</h2><p>Clusters group related articles; open one to compare coverage.</p></div><Link href="/stories" className="text-link">All stories <ArrowUpRight size={13} /></Link></div>
        <div className="filter-bar" aria-label="Story filters">
          <select className="filter-select" aria-label="Filter by language" value={language} onChange={(event) => setLanguage(event.target.value)}><option value="">All languages</option>{(overview?.by_language || []).map((row) => <option key={row.label} value={row.label}>{languageName(row.label)}</option>)}</select>
          <select className="filter-select" aria-label="Filter by source" value={sourceId} onChange={(event) => setSourceId(event.target.value)}><option value="">All sources</option>{sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}</select>
          <input className="filter-input" aria-label="From date" type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
          <input className="filter-input" aria-label="To date" type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
          {(language || sourceId || fromDate || toDate) && <button className="btn-secondary" onClick={() => { setLanguage(""); setSourceId(""); setFromDate(""); setToDate(""); }}><RefreshCw size={12} /> Clear</button>}
        </div>
        {loading ? <div className="loading-state">Loading story clusters…</div> : stories.length ? <div className="story-grid">{stories.slice(0, 6).map((story, index) => <StoryTile key={story.id} story={story} index={index} />)}</div> : <div className="empty-state">No stories match those filters. Clear a filter to see more of the sample.</div>}
        <p className="page-footer-note">Coverage measurements reflect only the records in this local sample. AI-derived analysis is an aid for research review and does not establish objective media bias.</p>
      </section>
      <span className="sr-only">API endpoint: {API}</span>
    </>
  );
}

function Metric({ label, value, foot, icon }: { label: string; value: number | undefined; foot: string; icon: React.ReactNode }) {
  return <div className="metric-card"><div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div><div className="metric-value">{value ?? "—"}</div><div className="metric-foot">{foot}</div></div>;
}

function StoryTile({ story, index }: { story: StoryCard; index: number }) {
  return <Link className="story-card" href={`/stories/${story.id}`} style={{ animationDelay: `${index * 40}ms` }}>
    <div className="story-card-top"><span className="eyebrow">STORY / {String(index + 1).padStart(2, "0")}</span>{story.is_synthetic && <span className="synthetic-pill">Synthetic</span>}</div>
    <h3>{story.canonical_title.replace(/^\[SYNTHETIC\]\s*/i, "")}</h3>
    <p className="story-summary">{story.summary}</p>
    <div className="story-card-foot"><span>{story.article_count} articles · {story.sources.length} sources</span><div className="language-pills">{story.languages.slice(0, 4).map((code) => <span className="language-pill" key={code}>{code}</span>)}</div></div>
  </Link>;
}
