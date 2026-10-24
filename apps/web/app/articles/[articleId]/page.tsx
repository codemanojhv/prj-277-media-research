"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { apiGet, apiPost, formatDate, languageName, type ArticleCard } from "@/lib/api";
import PublicReactionPanel from "@/components/PublicReactionPanel";

type ArticleDetail = ArticleCard & {
  raw_content: string;
  content: string;
  author: string | null;
  content_hash: string;
  collected_at: string | null;
  processed_at: string | null;
  story?: { id: number; canonical_title: string } | null;
  analysis: null | {
    goi_relevance_score: number;
    goi_relevance_threshold: number;
    is_goi_relevant: boolean;
    relevance_reasons: string[];
    sentiment: string;
    sentiment_score: number;
    sentiment_confidence: number;
    summary: string;
    key_points: { text: string; type: string; confidence: number }[];
    topics: { topic: string; confidence: number; evidence: string }[];
    entities: { text: string; type: string; confidence: number; evidence: string }[];
    claims: { text: string; type: string; confidence: number }[];
    concerns: { text: string; type: string; confidence: number }[];
    positive_aspects: { text: string; type: string; confidence: number }[];
    evidence: {
      sentiment: string[];
      topics: string[];
      summary: string[];
      gemini_generation?: {
        provider: string;
        model: string;
        input_characters: number;
        input_truncated: boolean;
        generated_at: string;
        key_points: { text: string; evidence: string }[];
        note: string;
      };
      gemini_note?: string;
      provider_decisions?: {
        provider: string;
        model: string;
        confidence_threshold: number;
        input_characters: number;
        input_truncated: boolean;
        note: string;
        relevance: { probability_yes: number; threshold: number; effective_label: string };
        sentiment: { choice: string; confidence: number; effective_label: string; used: boolean; probabilities: Record<string, number> };
        primary_topic: { choice: string; confidence: number; used_in_topic_counts: boolean };
      };
    };
    model: string;
    created_at: string | null;
  };
};

export default function ArticleDetailPage() {
  const params = useParams<{ articleId: string }>();
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [error, setError] = useState("");
  const [analysisError, setAnalysisError] = useState("");
  const [reanalyzing, setReanalyzing] = useState(false);
  useEffect(() => { if (params.articleId) apiGet<ArticleDetail>(`/articles/${params.articleId}`).then(setArticle).catch((issue) => setError(issue.message)); }, [params.articleId]);
  async function runLiveAnalysis() {
    if (!article || reanalyzing) return;
    setReanalyzing(true);
    setAnalysisError("");
    try {
      const updated = await apiPost<ArticleDetail>(`/articles/${article.id}/analyze`, {});
      setArticle(updated);
    } catch (issue) {
      setAnalysisError(issue instanceof Error ? issue.message : "Live analysis could not be completed.");
    } finally {
      setReanalyzing(false);
    }
  }
  if (error) return <><Link className="back-link" href="/articles"><ArrowLeft size={13} /> Article index</Link><div className="error-state">{error}</div></>;
  if (!article) return <div className="loading-state">Loading article evidence…</div>;
  const analysis = article.analysis;
  const externalUrl = article.url.startsWith("http://") || article.url.startsWith("https://");
  let articleHost = "";
  if (externalUrl) {
    try { articleHost = new URL(article.url).hostname.toLowerCase(); } catch { articleHost = ""; }
  }
  const providerResultUrl = ["news.google.com", "www.bing.com", "bing.com"].includes(articleHost);
  const segments = article.content.split(/(?<=[.!?।])\s+/).filter(Boolean);

  return <>
    <div className="detail-header"><Link className="back-link" href={article.story ? `/stories/${article.story.id}` : "/articles"}><ArrowLeft size={13} /> {article.story ? "Back to story" : "Article index"}</Link><p className="eyebrow">ARTICLE EVIDENCE / RECORD {String(article.id).padStart(4, "0")}</p><h1 className="detail-title">{article.title.replace(/^\[SYNTHETIC\]\s*/i, "")}</h1><div className="detail-meta"><span>{article.source.name}</span><span>·</span><span>{languageName(article.language)} ({Math.round(article.language_confidence * 100)}% detected)</span><span>·</span><span>{article.region || "Region not supplied"}</span><span>·</span><span>{formatDate(article.published_at)}</span>{article.is_synthetic && <span className="synthetic-pill">Synthetic sample</span>}</div></div>

    <div className="article-layout">
      <div>
        <PublicReactionPanel articleId={article.id} synthetic={article.is_synthetic} />
        <section className="panel detail-section" style={{ marginBottom: 13 }}><div className="section-head" style={{ margin: "0 0 10px" }}><div><h2>Article text</h2><p>Cleaned text stored beside the original collected content.</p></div>{externalUrl && <a className="text-link" href={article.url} target="_blank" rel="noreferrer">{providerResultUrl ? "Open news result" : "Open source"} <ExternalLink size={12} /></a>}</div>
          {article.is_synthetic && <div className="note-box">Synthetic classroom sample, not a real article or report. The sample is intended to demonstrate the research workflow only.</div>}
          {article.content_kind === "feed_excerpt" && <div className="note-box">Feed excerpt only. The publisher page could not be captured, so analysis is limited to text returned by the news feed.</div>}
          {article.collection_method === "online_search" && article.search_query && <div className="note-box">Collected from an online topic search: “{article.search_query}”. The search provider is recorded below as discovery provenance.</div>}
          <div className="article-body">{segments.map((segment, index) => <p key={index}>{segment}</p>)}</div>
          <details style={{ marginTop: 15, color: "#788078", fontSize: 10 }}><summary style={{ cursor: "pointer" }}>Show raw collected content</summary><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", background: "#f1f0e9", padding: 12, borderRadius: 6, fontSize: 9 }}>{article.raw_content}</pre></details>
        </section>

        <section className="panel detail-section"><div className="section-head" style={{ margin: "0 0 12px" }}><div><h2>Analysis evidence</h2><p>Quoted snippets are checked against this article's stored text.</p></div>{!article.is_synthetic && <button className="btn-secondary" type="button" onClick={runLiveAnalysis} disabled={reanalyzing}>{reanalyzing ? "Running JEV + Gemini…" : "Run live analysis"}</button>}</div>
          {analysisError && <div className="note-box" role="status">{analysisError}</div>}
          {reanalyzing && <div className="count-mono" style={{ marginBottom: 10 }}>The hosted service is analyzing the stored publisher text with configured providers.</div>}
          {analysis ? <>
            <AnalysisBlock title={analysis.evidence.gemini_generation ? "Summary · Gemini inference" : "Summary · local extraction"} value={analysis.summary} evidence={analysis.evidence.summary} />
            {analysis.evidence.gemini_generation && <>
              <div className="analysis-block"><h3>Key points · Gemini-generated</h3>{analysis.evidence.gemini_generation.key_points.map((point, index) => <div key={`${index}-${point.evidence}`} style={{ marginTop: index ? 10 : 0 }}><p style={{ color: "#516058", fontSize: 11, lineHeight: 1.6, margin: "0 0 5px" }}>{point.text}</p><Evidence evidence={[point.evidence]} /></div>)}<div className="count-mono" style={{ marginTop: 8 }}>{analysis.evidence.gemini_generation.model} · {analysis.evidence.gemini_generation.input_characters.toLocaleString()} input characters{analysis.evidence.gemini_generation.input_truncated ? " · source excerpt was bounded" : ""}</div><div className="count-mono" style={{ marginTop: 4 }}>{analysis.evidence.gemini_generation.note}</div></div>
            </>}
            {analysis.evidence.gemini_note && <div className="note-box">{analysis.evidence.gemini_note}</div>}
            {analysis.evidence.provider_decisions && <div className="note-box"><strong>{analysis.evidence.provider_decisions.provider} · {analysis.evidence.provider_decisions.model}</strong><br />{analysis.evidence.provider_decisions.note}<br /><br />JEV article tone: {analysis.evidence.provider_decisions.sentiment.effective_label} ({Math.round(analysis.evidence.provider_decisions.sentiment.confidence * 100)}%); primary topic: {analysis.evidence.provider_decisions.primary_topic.choice}. {analysis.evidence.provider_decisions.input_truncated && "The article text sent to JEV was truncated to the configured character limit."}</div>}
            <AnalysisBlock title="Key claims" evidence={analysis.claims.map((claim) => claim.text)} confidence={analysis.claims[0] ? Math.round(analysis.claims[0].confidence * 100) : undefined} />
            <AnalysisBlock title="Concerns extracted" evidence={analysis.concerns.map((item) => item.text)} confidence={analysis.concerns[0] ? Math.round(analysis.concerns[0].confidence * 100) : undefined} />
            <AnalysisBlock title="Positive aspects extracted" evidence={analysis.positive_aspects.map((item) => item.text)} confidence={analysis.positive_aspects[0] ? Math.round(analysis.positive_aspects[0].confidence * 100) : undefined} />
          </> : <div className="empty-state">Analysis is pending. Start the pipeline from the API.</div>}
        </section>
      </div>

      <aside>
        <section className="panel detail-section" style={{ marginBottom: 13 }}><h2>Model interpretation</h2>{analysis ? <>
          <div className="analysis-block"><h3>Article tone · inferred</h3><span className={`badge ${analysis.sentiment}`}>{analysis.sentiment}</span><span className="confidence">{Math.round(analysis.sentiment_confidence * 100)}% confidence</span><div className="count-mono" style={{ marginTop: 6 }}>Tone of the article text; audience views are summarized separately above.</div><Evidence evidence={analysis.evidence.sentiment} /></div>
          <div className="analysis-block"><h3>GoI relevance · calculated</h3><div className="analysis-value">{analysis.is_goi_relevant ? "Relevant in this sample" : "Below threshold"}<span className="confidence">{Math.round(analysis.goi_relevance_score * 100)}%</span></div><div className="count-mono" style={{ marginTop: 5 }}>Threshold {Math.round(analysis.goi_relevance_threshold * 100)}%</div><div className="topic-chip-list" style={{ marginTop: 7 }}>{analysis.relevance_reasons.map((reason) => <span key={reason} className="topic-chip">{reason}</span>)}</div></div>
          <div className="analysis-block"><h3>Topics · inferred</h3><div className="topic-chip-list">{analysis.topics.map((topic) => <span className="topic-chip" key={topic.topic}>{topic.topic}<small>{Math.round(topic.confidence * 100)}%</small></span>)}</div></div>
          <div className="analysis-block"><h3>Entities · extracted</h3><div className="topic-chip-list">{analysis.entities.length ? analysis.entities.map((entity, index) => <span className="topic-chip" key={`${entity.text}-${index}`}>{entity.text}<small>{entity.type}</small></span>) : <span className="count-mono">None detected</span>}</div></div>
        </> : <div className="empty-state">No analysis available.</div>}</section>

        <section className="panel detail-section"><h2>Provenance</h2><dl className="provenance-grid"><dt>Source</dt><dd>{article.source.name}</dd><dt>Published</dt><dd>{formatDate(article.published_at)}</dd><dt>Collected</dt><dd>{formatDate(article.collected_at)}</dd><dt>Processed</dt><dd>{formatDate(article.processed_at)}</dd><dt>Collection</dt><dd>{article.collection_method.replaceAll("_", " ")}</dd><dt>Captured text</dt><dd>{article.content_kind === "feed_excerpt" ? "Feed excerpt" : article.content_kind === "synthetic_text" ? "Synthetic demo text" : "Publisher page text"}</dd><dt>{providerResultUrl ? "Provider result" : "Source URL"}</dt><dd>{providerResultUrl ? `Direct article URL not exposed by the feed. Publisher: ${article.source.domain || article.source.name}.` : externalUrl ? <a className="source-link" href={article.url} target="_blank" rel="noreferrer">{article.source.domain || article.url}</a> : "Synthetic sample; no external source URL"}</dd>{article.discovery_url && <><dt>Discovery link</dt><dd><a className="source-link" href={article.discovery_url} target="_blank" rel="noreferrer">Open provider result</a></dd></>}{article.search_query && <><dt>Search terms</dt><dd>{article.search_query}</dd></>}{article.research_job_id && <><dt>Research job</dt><dd><Link className="source-link" href={`/research?job=${article.research_job_id}`}>Online search #{article.research_job_id}</Link></dd></>}<dt>Content hash</dt><dd>{article.content_hash.slice(0, 18)}…</dd></dl></section>
      </aside>
    </div>
    <p className="page-footer-note">All classifications and summaries are system-generated interpretations. Review the source text; confidence does not establish factual correctness.</p>
  </>;
}

function AnalysisBlock({ title, value, evidence, confidence }: { title: string; value?: string; evidence?: string[]; confidence?: number }) {
  return <div className="analysis-block"><h3>{title}{confidence !== undefined && <span className="confidence">{confidence}% confidence</span>}</h3>{value && <p style={{ color: "#516058", fontSize: 11, lineHeight: 1.65, margin: "0 0 7px" }}>{value}</p>}<Evidence evidence={evidence || []} /></div>;
}

function Evidence({ evidence }: { evidence: string[] }) {
  return evidence.length ? <div className="evidence-list">{evidence.map((snippet, index) => <div className="evidence-quote" key={index}>“{snippet}”</div>)}</div> : <span className="count-mono">No supporting snippet extracted.</span>;
}
