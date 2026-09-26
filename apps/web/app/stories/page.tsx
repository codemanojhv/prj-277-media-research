"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { apiGet, formatDate, languageName, type StoryCard } from "@/lib/api";

type Language = { language: string; count: number };

export default function StoriesPage() {
  const [items, setItems] = useState<StoryCard[]>([]);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [language, setLanguage] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => { apiGet<{ items: Language[] }>("/languages").then((payload) => setLanguages(payload.items)).catch((issue) => setError(issue.message)); }, []);
  useEffect(() => {
    const params = new URLSearchParams();
    if (language) params.set("language", language);
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);
    setLoading(true);
    apiGet<{ items: StoryCard[] }>(`/stories?${params}`).then((payload) => { setItems(payload.items); setError(""); }).catch((issue) => setError(issue.message)).finally(() => setLoading(false));
  }, [language, fromDate, toDate]);

  return <>
    <div className="page-heading-row"><div><p className="eyebrow">STORY INDEX / CLUSTERED COVERAGE</p><h1 className="page-title">Stories</h1><p className="page-lede">Related articles are grouped into candidate story sets for comparison. Each set opens into its linked source evidence.</p></div><div className="heading-meta"><strong>{items.length} GROUPS</strong>Filtered view of stored records</div></div>
    {error && <div className="error-state" role="alert">{error}. Start the local demo with <code>npm run demo</code>.</div>}
    <div className="panel" style={{ padding: 16, marginBottom: 13 }}><div className="filter-bar" style={{ margin: 0 }}><select className="filter-select" aria-label="Filter stories by language" value={language} onChange={(event) => setLanguage(event.target.value)}><option value="">All languages</option>{languages.map((item) => <option key={item.language} value={item.language}>{languageName(item.language)} · {item.count}</option>)}</select><input className="filter-input" aria-label="From date" type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} /><input className="filter-input" aria-label="To date" type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} /></div></div>
    {loading ? <div className="loading-state">Loading story clusters…</div> : items.length ? <div className="story-grid">{items.map((story, index) => <Link className="story-card" key={story.id} href={`/stories/${story.id}`} style={{ animationDelay: `${index * 35}ms` }}>
      <div className="story-card-top"><span className="eyebrow">CLUSTER / {String(index + 1).padStart(2, "0")}</span>{story.is_synthetic && <span className="synthetic-pill">Synthetic</span>}</div><h3>{story.canonical_title.replace(/^\[SYNTHETIC\]\s*/i, "")}</h3><p className="story-summary">{story.summary}</p><div className="story-card-foot"><span>{story.article_count} articles · {story.sources.length} sources</span><div className="language-pills">{story.languages.map((code) => <span className="language-pill" key={code}>{code}</span>)}</div></div><div className="story-card-foot" style={{ borderTop: 0, paddingTop: 7, marginTop: 0 }}><span>Updated {formatDate(story.last_updated)}</span><span className="text-link">Compare <ArrowUpRight size={12} /></span></div>
    </Link>)}</div> : <div className="empty-state">No stories match the selected filters.</div>}
    <p className="page-footer-note">Story groups are candidates, not verified event matches. Check the linked article text and sources before drawing conclusions.</p>
  </>;
}
