"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { apiGet, formatDate, languageName, type ArticleCard } from "@/lib/api";

type Source = { id: number; name: string; language: string };

export default function ArticlesPage() {
  const [articles, setArticles] = useState<ArticleCard[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [language, setLanguage] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => { apiGet<{ items: Source[] }>("/sources").then((payload) => setSources(payload.items)).catch((issue) => setError(issue.message)); }, []);
  useEffect(() => {
    const params = new URLSearchParams({ limit: "100" });
    if (language) params.set("language", language);
    if (sourceId) params.set("source_id", sourceId);
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);
    setLoading(true);
    apiGet<{ items: ArticleCard[]; count: number }>(`/articles?${params}`).then((payload) => { setArticles(payload.items); setCount(payload.count); setError(""); }).catch((issue) => setError(issue.message)).finally(() => setLoading(false));
  }, [language, sourceId, fromDate, toDate]);

  return <>
    <div className="page-heading-row"><div><p className="eyebrow">ARTICLE INDEX / SOURCE RECORDS</p><h1 className="page-title">Articles</h1><p className="page-lede">Browse source records and open their analysis, evidence snippets, and collection details.</p></div><div className="heading-meta"><strong>{count} RECORDS</strong>Filtered stored articles</div></div>
    {error && <div className="error-state">{error}. Start the local demo with <code>npm run demo</code>.</div>}
    <div className="panel" style={{ padding: 16, marginBottom: 13 }}><div className="filter-bar" style={{ margin: 0 }}>
      <select className="filter-select" aria-label="Filter by language" value={language} onChange={(event) => setLanguage(event.target.value)}><option value="">All languages</option>{[...new Set(sources.map((source) => source.language))].sort().map((code) => <option value={code} key={code}>{languageName(code)}</option>)}</select>
      <select className="filter-select" aria-label="Filter by source" value={sourceId} onChange={(event) => setSourceId(event.target.value)}><option value="">All sources</option>{sources.map((source) => <option value={source.id} key={source.id}>{source.name}</option>)}</select>
      <input className="filter-input" aria-label="From date" type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} /><input className="filter-input" aria-label="To date" type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
    </div></div>
    <div className="panel">
      {loading ? <div className="loading-state" style={{ margin: 14 }}>Loading articles…</div> : articles.length ? <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Article</th><th>Source</th><th>Language</th><th>Sentiment</th><th>Date</th><th></th></tr></thead><tbody>{articles.map((article) => <tr key={article.id}><td><Link className="data-title" href={`/articles/${article.id}`}>{article.title.replace(/^\[SYNTHETIC\]\s*/i, "")}</Link><div style={{ color: "#899087", fontSize: 9, marginTop: 4 }}>{article.summary}</div></td><td>{article.source.name}</td><td>{languageName(article.language)}</td><td><span className={`badge ${article.sentiment}`}>{article.sentiment}</span></td><td>{formatDate(article.published_at)}</td><td><Link href={`/articles/${article.id}`} aria-label={`Open ${article.title}`}><ArrowUpRight size={14} color="#809087" /></Link></td></tr>)}</tbody></table></div> : <div className="empty-state" style={{ margin: 14 }}>No articles match these filters.</div>}
    </div>
    <p className="page-footer-note">The synthetic sample has no external source pages. Imported articles retain their supplied public URL and collection timestamp.</p>
  </>;
}
