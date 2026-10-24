"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, ArrowUpRight, Languages, LockKeyhole, Scissors } from "lucide-react";
import { apiDelete, apiGet, apiPatch, apiPost, formatDate, languageName, type StoryDetail } from "@/lib/api";

export default function StoryDetailPage() {
  const params = useParams<{ storyId: string }>();
  const hosted = process.env.NEXT_PUBLIC_DEPLOYMENT_LABEL?.includes("CLOUDFLARE") || false;
  const [story, setStory] = useState<StoryDetail | null>(null);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [articleId, setArticleId] = useState("");
  const [mergeId, setMergeId] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  async function reload() {
    if (!params.storyId) return;
    const current = await apiGet<StoryDetail>(`/stories/${params.storyId}`);
    setStory(current);
    setTitle(current.canonical_title);
    setSummary(current.summary);
  }
  useEffect(() => { if (params.storyId) void reload().catch((issue) => setError(issue.message)); }, [params.storyId]);

  async function saveStory(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try { await apiPatch(`/stories/${params.storyId}`, { canonical_title: title, summary }); await reload(); setNotice("Story details saved as a manual curation."); }
    catch (issue) { setError(issue instanceof Error ? issue.message : "Story details could not be saved."); }
    finally { setBusy(false); }
  }
  async function addArticle(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try { await apiPost(`/stories/${params.storyId}/articles`, { article_id: Number(articleId) }); await reload(); setArticleId(""); setNotice("Article assigned to this story."); }
    catch (issue) { setError(issue instanceof Error ? issue.message : "Article could not be assigned."); }
    finally { setBusy(false); }
  }
  async function removeArticle(id: number) {
    setBusy(true); setError(""); setNotice("");
    try { await apiDelete(`/stories/${params.storyId}/articles/${id}`); await reload(); setNotice(`Article ${id} removed from this story.`); }
    catch (issue) { setError(issue instanceof Error ? issue.message : "Article could not be removed."); }
    finally { setBusy(false); }
  }
  async function mergeStory(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try { await apiPost(`/stories/${params.storyId}/merge`, { other_story_id: Number(mergeId) }); await reload(); setMergeId(""); setNotice("Story groups merged and protected from automatic re-clustering."); }
    catch (issue) { setError(issue instanceof Error ? issue.message : "The story groups could not be merged."); }
    finally { setBusy(false); }
  }

  if (error) return <><Link className="back-link" href="/stories"><ArrowLeft size={13} /> All stories</Link><div className="error-state">{error}</div></>;
  if (!story) return <div className="loading-state">Loading the article comparison…</div>;

  const languageRows = story.comparison.language_comparison;
  const sources = [...new Set(story.articles.map((article) => article.source.name))];
  return <>
    <div className="detail-header"><Link className="back-link" href="/stories"><ArrowLeft size={13} /> All stories</Link><p className="eyebrow">360° STORY VIEW / CLUSTER {String(story.id).padStart(3, "0")}</p><h1 className="detail-title">{story.canonical_title.replace(/^\[SYNTHETIC\]\s*/i, "")}</h1><div className="detail-meta"><span>{story.article_count} articles</span><span>·</span><span>{story.languages.length} languages</span><span>·</span><span>{sources.length} sources</span><span>·</span><span>First seen {formatDate(story.first_seen)}</span>{story.is_synthetic && <span className="synthetic-pill">Synthetic sample</span>}{story.is_manually_curated && <span className="manual-pill"><LockKeyhole size={10} /> MANUALLY CURATED</span>}</div><p className="detail-summary">{story.summary}</p></div>

    {!hosted && <section className="panel curation-panel"><div className="section-head"><div><h2>Researcher corrections</h2><p>These changes persist when the corpus is reprocessed.</p></div><span className="panel-kicker">{story.is_manually_curated ? "MANUAL OVERRIDE" : "AUTO CLUSTER"}</span></div>
      {error && <div className="error-state" role="alert">{error}</div>}{notice && <div className="success-state" role="status">{notice}</div>}
      <form className="curation-edit-form" onSubmit={saveStory}><label className="field-label">Story title<input className="filter-input" maxLength={500} required value={title} onChange={(event) => setTitle(event.target.value)} /></label><label className="field-label">Research summary<textarea className="research-textarea" maxLength={5000} value={summary} onChange={(event) => setSummary(event.target.value)} /></label><button className="btn-primary" type="submit" disabled={busy}>Save story details</button></form>
      <div className="curation-actions"><form onSubmit={addArticle}><label className="field-label">Add article by ID<input className="filter-input" type="number" min="1" required value={articleId} onChange={(event) => setArticleId(event.target.value)} placeholder="See the article ID in its URL" /></label><button className="btn-secondary" type="submit" disabled={busy}>Assign article</button></form><form onSubmit={mergeStory}><label className="field-label">Merge another story by ID<input className="filter-input" type="number" min="1" required value={mergeId} onChange={(event) => setMergeId(event.target.value)} placeholder="Enter the other story ID" /></label><button className="btn-secondary" type="submit" disabled={busy}>Merge groups</button></form></div>
    </section>}

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
      <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Language</th><th>Articles</th><th>Article tone</th><th>Main topics</th></tr></thead><tbody>{languageRows.map((row) => <tr key={row.language}><td><strong>{languageName(row.language)}</strong></td><td>{row.sample_size}</td><td>{Object.entries(row.sentiment_distribution).map(([key, count]) => `${key} ${count}`).join(" · ") || "—"}</td><td>{row.main_topics.map((item) => `${item.topic} (${item.count})`).join(", ") || "—"}</td></tr>)}</tbody></table></div>
    </section>

    <section className="panel detail-section" style={{ marginBottom: 13 }}><div className="section-head" style={{ margin: "0 0 11px" }}><div><h2>Source comparison</h2><p>Coverage attributes shown with each source’s article sample size.</p></div></div>
      <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Source</th><th>Language</th><th>Articles</th><th>Article tone</th><th>Topic emphasis</th></tr></thead><tbody>{story.comparison.source_comparison.map((row) => <tr key={row.source}><td><strong>{row.source}</strong></td><td>{languageName(row.language)}</td><td>{row.sample_size}</td><td>{Object.entries(row.sentiment_distribution).map(([key, count]) => `${key} ${count}`).join(" · ")}</td><td>{row.main_topics.map((item) => `${item.topic} (${item.count})`).join(", ") || "—"}</td></tr>)}</tbody></table></div>
    </section>

    <section className="panel detail-section"><div className="section-head" style={{ margin: "0 0 10px" }}><div><h2>Articles in this story</h2><p>Open a source record or remove it from the current group.</p></div><span className="panel-kicker">{story.article_count} RECORDS</span></div>
      <div className="curated-article-list">{story.articles.map((article) => <div className="curated-article-row" key={article.id}><Link href={`/articles/${article.id}`}><strong>{article.title.replace(/^\[SYNTHETIC\]\s*/i, "")}</strong><span>#{article.id} · {article.source.name} · {languageName(article.language)} · {article.region || "Region not supplied"}</span></Link><span className={`badge ${article.sentiment}`}>{article.sentiment}</span><span className="count-mono">{formatDate(article.published_at)}</span><button className="btn-secondary" type="button" disabled={busy} onClick={() => void removeArticle(article.id)}><Scissors size={12} /> Remove</button></div>)}</div>
    </section>
    <p className="page-footer-note">Topic and article-tone values are inferences from a small sample. The source articles remain the evidence; this comparison does not classify outlet bias.</p>
  </>;
}
