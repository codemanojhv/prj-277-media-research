"use client";

import { useEffect, useState } from "react";
import { ExternalLink, LoaderCircle, MessageCircle, Search } from "lucide-react";
import { apiGet, apiPost, formatDate, type PublicReactionReport } from "@/lib/api";

const labels = ["positive", "negative", "mixed"] as const;

function audienceView(distribution: PublicReactionReport["distribution"] | undefined) {
  const counts = {
    positive: distribution?.positive || 0,
    negative: distribution?.negative || 0,
    mixed: distribution?.mixed || 0,
    excluded: (distribution?.neutral || 0) + (distribution?.uncertain || 0),
  };
  const directional = counts.positive + counts.negative;
  const classified = directional + counts.mixed;
  if (!classified) return { label: "No directional signal", tone: "none", ...counts, directional, classified };
  if (!directional) return { label: "Mixed reactions", tone: "divided", ...counts, directional, classified };
  const balance = Math.abs(counts.positive - counts.negative) / directional;
  if (balance < 0.2) {
    return { label: "Divided", tone: "divided", ...counts, directional, classified };
  }
  return counts.positive > counts.negative
    ? { label: "Leans favorable", tone: "favorable", ...counts, directional, classified }
    : { label: "Leans critical", tone: "critical", ...counts, directional, classified };
}

function platformName(platform: string) {
  return platform === "hacker_news" ? "Hacker News" : "Bluesky";
}

export default function PublicReactionPanel({ articleId, synthetic }: { articleId: number; synthetic: boolean }) {
  const [report, setReport] = useState<PublicReactionReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (synthetic) return;
    let active = true;
    apiGet<PublicReactionReport>(`/articles/${articleId}/reactions`)
      .then((value) => { if (active && value.available) setReport(value); })
      .catch((issue) => { if (active) setError(issue instanceof Error ? issue.message : "Could not load the saved public reaction sample."); });
    return () => { active = false; };
  }, [articleId, synthetic]);

  async function searchReactions() {
    if (loading || synthetic) return;
    setLoading(true);
    setError("");
    try {
      const value = await apiPost<PublicReactionReport>(`/articles/${articleId}/reactions/collect`, {});
      setReport(value);
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Public reaction search could not be completed.");
    } finally {
      setLoading(false);
    }
  }

  const reactions = report?.reactions || [];
  const directionalReactions = reactions.filter((reaction) =>
    reaction.sentiment === "positive" || reaction.sentiment === "negative" || reaction.sentiment === "mixed"
  );
  const sampleCount = report?.sample_count || 0;
  const view = audienceView(report?.distribution);
  const matchedPlatforms = (report?.sources || []).filter((source) => source.count > 0).map((source) => source.label);

  return <section className="panel detail-section reaction-panel" aria-labelledby="public-reactions-heading">
    <div className="section-head reaction-panel-head">
      <div>
        <p className="eyebrow">PUBLIC DISCUSSION / READER REACTIONS</p>
        <h2 id="public-reactions-heading">What people are saying</h2>
        <p>The conclusion comes from matched public posts and comments, not the article’s own tone.</p>
      </div>
      {!synthetic && <button className="btn-primary" type="button" onClick={searchReactions} disabled={loading}>
        {loading ? <><LoaderCircle size={13} className="spin-icon" /> Searching public posts…</> : <><Search size={13} /> {report ? "Check for new reactions" : "Search public reactions"}</>}
      </button>}
    </div>

    {synthetic ? <div className="note-box">This is a synthetic classroom sample. Public reaction search is available for collected real articles.</div> : <>
      {error && <div className="error-state reaction-error" role="alert">{error}</div>}
        {loading && <div className="reaction-loading" role="status">Searching public Bluesky posts and Hacker News comments, then classifying matched reactions.</div>}
      {!report && !loading && <div className="reaction-empty"><MessageCircle size={18} /><span>Search public platforms for reactions to this article. Nothing is counted until matching posts are collected.</span></div>}

      {report && <div aria-live="polite">
        {report.cache_hit && <div className="count-mono reaction-cache-note">Showing a recent saved scan to avoid repeating paid AI calls.</div>}
        {report.status === "no_results" && <div className="note-box">No matching public reactions were found on the enabled sources. This does not mean no one reacted elsewhere.</div>}
        {report.status === "analysis_unavailable" && <div className="note-box">Public posts were collected, but online sentiment analysis was unavailable. The app has not assigned local-model labels.</div>}

        <div className="reaction-source-list" aria-label="Public source coverage">
          {(report.sources || []).map((source) => <div className="reaction-source" key={source.platform}>
            <span className={`reaction-source-dot ${source.status}`} />
            <strong>{source.label}</strong>
            <span>{source.status === "collected" ? `${source.count} matched` : source.status === "unavailable" ? "unavailable" : "no matches"}</span>
            <small>{source.note}</small>
          </div>)}
        </div>

        {sampleCount > 0 && <>
          <div className={`reaction-verdict ${view.tone}`} aria-live="polite">
            <span className="reaction-summary-label">Observed audience view · matched sample</span>
            <strong>{view.label}</strong>
            <p>{view.positive} favorable · {view.negative} critical · {view.mixed} mixed; {view.directional} clear-polarity reactions used for direction. {view.excluded} neutral/uncertain excluded.</p>
            <small>{matchedPlatforms.length ? `Matched on ${matchedPlatforms.join(" and ")}. ` : "No platform supplied a matched reaction. "}Likes, points, replies, and reposts are context, not extra votes.</small>
          </div>
          <div className="reaction-summary-grid">
            <div className="reaction-sample-count"><strong>{sampleCount}</strong><span>matched posts and comments</span></div>
          <div className="reaction-distribution">
              <div className="reaction-distribution-head"><h3>Classified reactions</h3><span>neutral and unclear excluded</span></div>
              {labels.map((label) => {
                const count = report.distribution?.[label] || 0;
                const width = Math.round(count / Math.max(1, view.classified) * 100);
                return <div className="reaction-bar-row" key={label}>
                  <span>{label}</span><div className="reaction-bar-track"><div className={`reaction-bar-fill ${label}`} style={{ width: `${width}%` }} /></div><strong>{count}</strong>
                </div>;
              })}
            </div>
          </div>

          {report.summary && <div className="reaction-ai-summary"><span className="reaction-summary-label">Discussion summary · sample only</span><p>{report.summary}</p>{report.summarizer && <small>{report.summarizer}</small>}</div>}
          {report.themes?.length ? <div className="reaction-themes"><h3>Recurring discussion themes</h3>{report.themes.map((theme, index) => <div className="reaction-theme" key={`${theme.label}-${index}`}><strong>{theme.label}</strong><div>{theme.evidence.map((evidence, evidenceIndex) => <blockquote key={`${evidenceIndex}-${evidence}`}>{evidence}</blockquote>)}</div></div>)}</div> : null}

          <div className="reaction-evidence-head"><h3>{directionalReactions.length ? "Matched public reactions" : "Collected reactions"}</h3><span>{report.classifier || "Online classifier unavailable"}</span></div>
          {reactions.length ? <div className="reaction-post-list">
            {reactions.map((reaction) => <article className="reaction-post" key={reaction.id}>
              <div className="reaction-post-top"><span className="reaction-platform">{platformName(reaction.platform)}</span><span className={`badge ${reaction.sentiment}`}>{reaction.sentiment}</span><span className="confidence">{Math.round(reaction.confidence * 100)}% model confidence</span></div>
              {reaction.discussion_title && <div className="reaction-thread-title">Thread: {reaction.discussion_title}</div>}
              <p>{reaction.text}</p>
              <div className="reaction-post-foot"><span>{reaction.match_basis === "article_link" ? "Article link match" : "Headline terms match"} · {formatDate(reaction.published_at)}</span><span>{reaction.likes} {reaction.engagement_label}{reaction.replies ? ` · ${reaction.replies} replies` : ""}{reaction.reposts ? ` · ${reaction.reposts} reposts` : ""}</span><a href={reaction.url} target="_blank" rel="noreferrer">View original <ExternalLink size={11} /></a></div>
            </article>)}
          </div> : <div className="reaction-empty">No favorable, critical, or mixed reactions were clear enough to use.</div>}
        </>}

        {!!report.notes?.length && <div className="reaction-notes">{report.notes.map((note, index) => <p key={`${index}-${note}`}>{note}</p>)}</div>}
        {report.collected_at && <div className="count-mono reaction-timestamp">Collected {formatDate(report.collected_at)} · search terms: {report.query}</div>}
      </div>}
    </>}
  </section>;
}
