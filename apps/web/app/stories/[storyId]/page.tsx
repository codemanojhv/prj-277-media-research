"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, Languages } from "lucide-react";
import { apiGet, formatDate, languageName, type StoryDetail } from "@/lib/api";

export default function StoryDetailPage() {
  const params = useParams<{ storyId: string }>();
  const [story, setStory] = useState<StoryDetail | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { if (params.storyId) apiGet<StoryDetail>(`/stories/${params.storyId}`).then(setStory).catch((issue) => setError(issue.message)); }, [params.storyId]);

  if (error) return <><Link className="back-link" href="/stories"><ArrowLeft size={13} /> All stories</Link><div className="error-state">{error}</div></>;
  if (!story) return <div className="loading-state">Loading the article comparison…</div>;

  const languageRows = story.comparison.language_comparison;
  const sources = [...new Set(story.articles.map((article) => article.source.name))];
  return <>
    <div className="detail-header"><Link className="back-link" href="/stories"><ArrowLeft size={13} /> All stories</Link><p className="eyebrow">360° STORY VIEW / CLUSTER {String(story.id).padStart(3, "0")}</p><h1 className="detail-title">{story.canonical_title.replace(/^\[SYNTHETIC\]\s*/i, "")}</h1><div className="detail-meta"><span>{story.article_count} articles</span><span>·</span><span>{story.languages.length} languages</span><span>·</span><span>{sources.length} sources</span><span>·</span><span>First seen {formatDate(story.first_seen)}</span>{story.is_synthetic && <span className="synthetic-pill">Synthetic sample</span>}</div><p className="detail-summary">{story.summary}</p></div>

    <div className="note-box">{story.comparison.interpretation_note}</div>
    <section className="detail-grid">
      <div className="panel detail-section"><div className="section-head" style={{ margin: "0 0 13px" }}><div><h2>Shared information</h2><p>Signals found in more than one article in this cluster.</p></div><span className="panel-kicker">ARTICLE-LINKED</span></div>
        <div className="analysis-block"><h3>Shared topic labels</h3><div className="topic-chip-list">{story.comparison.shared_narrative.topics.length ? story.comparison.shared_narrative.topics.map((item) => <span className="topic-chip" key={item.topic}>{item.topic}<small>{item.sample_count} articles</small></span>) : <span className="count-mono">No repeated topic labels in this sample.</span>}</div></div>
        <div className="analysis-block" style={{ marginTop: 16 }}><h3>Repeated entities</h3><div className="topic-chip-list">{story.comparison.shared_narrative.entities.length ? story.comparison.shared_narrative.entities.map((item) => <span className="topic-chip" key={item.entity}>{item.entity}<small>{item.sample_count} mentions</small></span>) : <span className="count-mono">No repeated entities detected.</span>}</div></div>
      </div>
      <div className="panel detail-section"><div className="section-head" style={{ margin: "0 0 13px" }}><div><h2>Coverage differences</h2><p>Observed topic emphasis by language.</p></div><Languages size={16} color="#718778" /></div>
        {story.comparison.coverage_differences.length ? <div className="comparison-list">{story.comparison.coverage_differences.slice(0, 4).map((item, index) => <div className="comparison-row" key={`${item.group_a}-${item.group_b}-${index}`}><span className="comparison-groups">{languageName(item.group_a)} ↔ {languageName(item.group_b)} · n {item.sample_sizes[item.group_a]} / {item.sample_sizes[item.group_b]}</span><p>{item.difference}</p><span className="count-mono">Article IDs: {item.article_ids.slice(0, 6).join(", ")}</span></div>)}</div> : <div className="empty-state">The available language samples show similar topic labels.</div>}
      </div>
    </section>

    <section className="panel detail-section" style={{ marginBottom: 13 }}><div className="section-head" style={{ margin: "0 0 11px" }}><div><h2>Language comparison</h2><p>Counts describe only the articles in this cluster.</p></div></div>
      <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Language</th><th>Articles</th><th>Sentiment distribution</th><th>Stance distribution</th><th>Main topics</th></tr></thead><tbody>{languageRows.map((row) => <tr key={row.language}><td><strong>{languageName(row.language)}</strong></td><td>{row.sample_size}</td><td>{Object.entries(row.sentiment_distribution).map(([key, count]) => `${key} ${count}`).join(" · ") || "—"}</td><td>{Object.entries(row.stance_distribution).map(([key, count]) => `${key} ${count}`).join(" · ") || "—"}</td><td>{row.main_topics.map((item) => `${item.topic} (${item.count})`).join(", ") || "—"}</td></tr>)}</tbody></table></div>
    </section>

    <section className="panel detail-section" style={{ marginBottom: 13 }}><div className="section-head" style={{ margin: "0 0 11px" }}><div><h2>Source comparison</h2><p>Coverage attributes shown with each source’s article sample size.</p></div></div>
      <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Source</th><th>Language</th><th>Articles</th><th>Sentiment</th><th>Stance</th><th>Topic emphasis</th></tr></thead><tbody>{story.comparison.source_comparison.map((row) => <tr key={row.source}><td><strong>{row.source}</strong></td><td>{languageName(row.language)}</td><td>{row.sample_size}</td><td>{Object.entries(row.sentiment_distribution).map(([key, count]) => `${key} ${count}`).join(" · ")}</td><td>{Object.entries(row.stance_distribution).map(([key, count]) => `${key} ${count}`).join(" · ")}</td><td>{row.main_topics.map((item) => `${item.topic} (${item.count})`).join(", ") || "—"}</td></tr>)}</tbody></table></div>
    </section>

    <section className="panel detail-section"><div className="section-head" style={{ margin: "0 0 10px" }}><div><h2>Articles in this story</h2><p>Open an article to inspect its evidence and analysis provenance.</p></div><span className="panel-kicker">{story.article_count} RECORDS</span></div>
      <div className="article-list">{story.articles.map((article) => <Link className="article-row" href={`/articles/${article.id}`} key={article.id}><div><div className="article-row-title">{article.title.replace(/^\[SYNTHETIC\]\s*/i, "")}</div><div className="article-row-meta">{article.source.name} · {languageName(article.language)} · {article.region || "Region not supplied"}</div></div><span className={`badge ${article.sentiment}`}>{article.sentiment}</span><span className="article-row-date count-mono">{formatDate(article.published_at)}</span><ArrowUpRight size={14} color="#809087" /></Link>)}</div>
    </section>
    <p className="page-footer-note">Topic, sentiment, and stance values are inferences from a small sample. The source articles remain the evidence; this comparison does not classify outlet bias.</p>
  </>;
}
