"use client";

import { useEffect, useState } from "react";
import { BarChart3, Languages, RadioTower } from "lucide-react";
import { apiGet } from "@/lib/api";

type BreakdownItem = {
  label: string;
  sample_size: number;
  languages: Record<string, number>;
  sources: string[];
  sentiment_distribution: Record<string, number>;
  topic_distribution: { topic: string; count: number }[];
};
type Breakdown = { dimension: string; sample_size: number; items: BreakdownItem[]; interpretation_note: string };

function Snapshot({ item }: { item: BreakdownItem }) {
  const topics = item.topic_distribution.slice(0, 3);
  const positive = item.sentiment_distribution.positive || 0;
  const negative = item.sentiment_distribution.negative || 0;
  const mixed = item.sentiment_distribution.mixed || 0;
  const total = Math.max(1, positive + negative + mixed + (item.sentiment_distribution.neutral || 0) + (item.sentiment_distribution.uncertain || 0));
  return <article className="breakdown-row">
    <div className="breakdown-label"><strong>{item.label}</strong><span>{Object.entries(item.languages).map(([language, count]) => `${language.toUpperCase()} ${count}`).join(" · ")}</span></div>
    <div className="breakdown-track" aria-label={`${item.sample_size} articles; ${positive} positive, ${negative} negative, ${mixed} mixed`}>
      <i className="sentiment-positive" style={{ width: `${positive / total * 100}%` }} />
      <i className="sentiment-mixed" style={{ width: `${mixed / total * 100}%` }} />
      <i className="sentiment-negative" style={{ width: `${negative / total * 100}%` }} />
    </div>
    <div className="breakdown-summary"><b>{item.sample_size}</b><span>{topics.map((topic) => `${topic.topic} (${topic.count})`).join(" · ") || "No topic labels"}</span></div>
  </article>;
}

export default function AnalyticsPage() {
  const [languages, setLanguages] = useState<Breakdown | null>(null);
  const [sources, setSources] = useState<Breakdown | null>(null);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [corpus, setCorpus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams();
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);
    if (corpus) params.set("is_synthetic", corpus);
    const query = params.toString();
    setLoading(true);
    Promise.all([
      apiGet<Breakdown>(`/analytics/breakdown?dimension=language&${query}`),
      apiGet<Breakdown>(`/analytics/breakdown?dimension=source&${query}`),
    ]).then(([languageData, sourceData]) => {
      setLanguages(languageData);
      setSources(sourceData);
      setError("");
    }).catch((issue) => setError(issue.message)).finally(() => setLoading(false));
  }, [fromDate, toDate, corpus]);

  return <>
    <div className="page-heading-row"><div><p className="eyebrow">SAMPLE ANALYTICS / LANGUAGE + SOURCE</p><h1 className="page-title">Coverage patterns</h1><p className="page-lede">Compare the stored sample by language and publisher. These counts describe the records collected under your selected filters.</p></div><div className="heading-meta"><strong>{(languages?.sample_size || 0).toLocaleString()} ARTICLES</strong>Current filtered sample</div></div>
    <section className="panel analytics-filters"><div><span className="eyebrow">FILTER THE SAMPLE</span><p>Choose a date window and whether to include the classroom corpus.</p></div><div className="filter-bar"><label><span>From</span><input className="filter-input" type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} /></label><label><span>To</span><input className="filter-input" type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} /></label><label><span>Records</span><select className="filter-select" value={corpus} onChange={(event) => setCorpus(event.target.value)}><option value="">All stored records</option><option value="false">Collected / imported</option><option value="true">Synthetic classroom data</option></select></label></div></section>
    {error && <div className="error-state" role="alert">{error}</div>}
    {loading ? <div className="loading-state">Building sample comparisons…</div> : <div className="analytics-grid">
      <section className="panel breakdown-panel"><div className="section-head"><div><h2><Languages size={16} /> By language</h2><p>Article counts and observed sentiment/topic mix.</p></div><span className="panel-kicker">{languages?.items.length || 0} GROUPS</span></div>
        {languages?.items.length ? languages.items.map((item) => <Snapshot key={item.label} item={item} />) : <div className="empty-state">No records match these filters.</div>}
      </section>
      <section className="panel breakdown-panel"><div className="section-head"><div><h2><RadioTower size={16} /> By source</h2><p>Publisher samples, split by detected language.</p></div><span className="panel-kicker">{sources?.items.length || 0} SOURCES</span></div>
        {sources?.items.length ? sources.items.map((item) => <Snapshot key={item.label} item={item} />) : <div className="empty-state">No sources match these filters.</div>}
      </section>
    </div>}
    <div className="note-box analytics-note"><BarChart3 size={15} /><span>{languages?.interpretation_note || "Sample sizes differ by source and language; review the underlying article records before drawing conclusions."}</span></div>
  </>;
}
