"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, Check, ExternalLink, LoaderCircle, Radio, Search, Sparkles } from "lucide-react";
import { apiGet, apiPost, formatDate, languageName, type ArticleCard, type ResearchJob, type ResearchOptions, type StoryCard } from "@/lib/api";

type JobList = { items: ResearchJob[]; count: number };
type ArticleList = { items: ArticleCard[]; count: number };
type StoryList = { items: StoryCard[]; count: number };

export default function ResearchSearchPage() {
  const [options, setOptions] = useState<ResearchOptions | null>(null);
  const [topic, setTopic] = useState("");
  const [aliases, setAliases] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [languages, setLanguages] = useState<string[]>(["en"]);
  const [outletIds, setOutletIds] = useState<string[]>([]);
  const [perLanguageLimit, setPerLanguageLimit] = useState(3);
  const [history, setHistory] = useState<ResearchJob[]>([]);
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [activeJob, setActiveJob] = useState<ResearchJob | null>(null);
  const [articles, setArticles] = useState<ArticleCard[]>([]);
  const [stories, setStories] = useState<StoryCard[]>([]);
  const [resultsLoad, setResultsLoad] = useState<{ jobId: number; status: "loading" | "loaded" | "failed" } | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([apiGet<ResearchOptions>("/research/options"), apiGet<JobList>("/research/jobs")])
      .then(([researchOptions, jobs]) => {
        setOptions(researchOptions);
        setFromDate(researchOptions.default_from_date);
        setToDate(researchOptions.default_to_date);
        setHistory(jobs.items);
      })
      .catch((issue) => setError(issue.message))
      .finally(() => setLoadingOptions(false));
  }, []);

  useEffect(() => {
    const jobId = Number(new URLSearchParams(window.location.search).get("job"));
    if (Number.isInteger(jobId) && jobId > 0) setActiveJobId(jobId);
  }, []);

  useEffect(() => {
    if (activeJobId === null) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => {
      try {
        const job = await apiGet<ResearchJob>(`/research/jobs/${activeJobId}`);
        if (cancelled) return;
        setActiveJob(job);
        if (job.status === "queued" || job.status === "running") {
          timer = setTimeout(refresh, 1500);
        } else {
          apiGet<JobList>("/research/jobs").then((payload) => { if (!cancelled) setHistory(payload.items); }).catch(() => undefined);
        }
      } catch (issue) {
        if (!cancelled) setError(issue instanceof Error ? issue.message : "Could not read the search status");
      }
    };
    void refresh();
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, [activeJobId]);

  useEffect(() => {
    if (!activeJob || activeJob.status !== "completed") {
      setArticles([]);
      setStories([]);
      setResultsLoad(null);
      return;
    }
    let cancelled = false;
    setResultsLoad({ jobId: activeJob.id, status: "loading" });
    Promise.all([
      apiGet<ArticleList>(`/articles?research_job_id=${activeJob.id}&limit=100`),
      apiGet<StoryList>(`/stories?research_job_id=${activeJob.id}&limit=100`),
    ]).then(([articleList, storyList]) => {
      if (!cancelled) {
        setArticles(articleList.items);
        setStories(storyList.items);
        setResultsLoad({ jobId: activeJob.id, status: "loaded" });
      }
    }).catch((issue) => {
      if (!cancelled) {
        setError(issue.message);
        setResultsLoad({ jobId: activeJob.id, status: "failed" });
      }
    });
    return () => { cancelled = true; };
  }, [activeJob]);

  const selectedOutletNames = useMemo(
    () => options?.outlets.filter((outlet) => outletIds.includes(outlet.id)).map((outlet) => outlet.name) ?? [],
    [options, outletIds],
  );

  const toggleValue = (values: string[], value: string, setValues: (value: string[]) => void) => {
    setValues(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  };

  const submitSearch = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    if (languages.length === 0) { setError("Choose at least one language to search."); return; }
    if (!topic.trim()) { setError("Enter a campaign, policy, or article topic."); return; }
    setSubmitting(true);
    setActiveJob(null);
    setArticles([]);
    setStories([]);
    try {
      const job = await apiPost<{ id: number; status: string }>("/research/search", {
        query: topic.trim(),
        aliases: aliases.split(/[\n,;]/).map((value) => value.trim()).filter(Boolean),
        from_date: fromDate,
        to_date: toDate,
        languages,
        outlet_ids: outletIds,
        per_language_limit: perLanguageLimit,
      });
      setActiveJobId(job.id);
      setHistory((current) => [{ id: job.id, job_type: "online-research", status: "queued", progress: 0, started_at: null, completed_at: null, error: null, metadata: { request: { query: topic.trim(), aliases: [], from_date: fromDate, to_date: toDate, languages, outlet_ids: outletIds, per_language_limit: perLanguageLimit } } }, ...current]);
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Search could not be started");
    } finally {
      setSubmitting(false);
    }
  };

  const result = activeJob?.metadata.result;
  const activeRequest = activeJob?.metadata.request;
  const visibleHistory = activeJob
    ? history.some((job) => job.id === activeJob.id)
      ? history.map((job) => job.id === activeJob.id ? activeJob : job)
      : [activeJob, ...history]
    : history;
  const resultStatus = resultsLoad && activeJob && resultsLoad.jobId === activeJob.id ? resultsLoad.status : "loading";
  const emptyResultsMessage = resultStatus === "loaded"
    ? "No new articles were stored for this query. Try broadening the dates or including more languages."
    : resultStatus === "failed" ? "Results could not be loaded. Select this search again to retry." : "Loading results for this search…";

  return <>
    <div className="page-heading-row research-heading">
      <div><p className="eyebrow">LIVE DISCOVERY / RESEARCH QUERY</p><h1 className="page-title">Find the coverage.</h1><p className="page-lede">Search public news coverage around a policy, campaign, or announcement. Collected records go straight into the evidence, analysis, and story comparison workflow.</p></div>
      <div className="heading-meta"><strong>SEARCH → ANALYZE → COMPARE</strong>{process.env.NEXT_PUBLIC_DEPLOYMENT_LABEL?.includes("CLOUDFLARE") ? "Stored in Cloudflare D1 with source links" : "Stored locally with source links"}</div>
    </div>

    <div className="research-note"><span className="research-note-icon"><Radio size={15} /></span><div><strong>Online news search</strong><span>Uses {options?.providers.join(", ") || "public news feeds"}. Selection narrows the sample; feeds may miss relevant reports. No model API key is required.</span></div><span className="research-key-status"><Check size={12} /> NO KEY NEEDED</span></div>

    {error && <div className="error-state" role="alert">{error}</div>}

    <div className="research-layout">
      <form className="panel research-form" onSubmit={submitSearch}>
        <div className="research-form-head"><span className="form-step">01</span><div><h2>Describe the coverage</h2><p>Use the official name, campaign name, or a specific article headline.</p></div></div>
        <label className="field-label" htmlFor="research-topic">Topic or initiative <span>required</span></label>
        <input id="research-topic" className="research-text-input" value={topic} onChange={(event) => setTopic(event.target.value)} maxLength={200} placeholder="e.g. Swachh Bharat Mission" required />
        <label className="field-label field-label-spaced" htmlFor="research-aliases">Other names or related phrases <span>optional</span></label>
        <textarea id="research-aliases" className="research-textarea" rows={2} value={aliases} onChange={(event) => setAliases(event.target.value)} placeholder={'e.g. Clean India campaign, SBM\nSeparate phrases with commas or new lines'} />

        <div className="research-form-head research-form-subhead"><span className="form-step">02</span><div><h2>Set the sample</h2><p>Dates apply to the publication date reported by the feed.</p></div></div>
        <div className="research-date-grid"><label className="research-field"><span>From</span><input className="filter-input" type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} required /></label><label className="research-field"><span>Through</span><input className="filter-input" type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} required /></label></div>

        <div className="research-form-head research-form-subhead"><span className="form-step">03</span><div><h2>Choose languages</h2><p>Language results are checked from the text, then filtered.</p></div></div>
        <div className="choice-grid language-choice-grid">{options?.languages.map((language) => <label className="choice-card" key={language.code}><input type="checkbox" checked={languages.includes(language.code)} onChange={() => toggleValue(languages, language.code, setLanguages)} /><span className="choice-check"><Check size={11} /></span><span>{language.label}</span></label>)}</div>

        <div className="research-form-head research-form-subhead"><span className="form-step">04</span><div><h2>Optionally select outlets</h2><p>{outletIds.length ? `${selectedOutletNames.length} selected` : "All discoverable outlets are included by default."}</p></div></div>
        <div className="outlet-choice-grid">{options?.outlets.map((outlet) => <label className="outlet-choice" key={outlet.id}><input type="checkbox" checked={outletIds.includes(outlet.id)} onChange={() => toggleValue(outletIds, outlet.id, setOutletIds)} /><span>{outlet.name}</span></label>)}</div>
        <div className="research-limit-row"><label htmlFor="per-language-limit">Maximum articles per language</label><select id="per-language-limit" className="filter-select" value={perLanguageLimit} onChange={(event) => setPerLanguageLimit(Number(event.target.value))}>{[1, 2, 3, 5, 8, 10].filter((count) => count <= (options?.maximum_articles_per_language ?? 1)).map((count) => <option value={count} key={count}>{count} {count === 1 ? "article" : "articles"}</option>)}</select></div>
        <button className="btn-primary research-submit" type="submit" disabled={submitting || loadingOptions || languages.length === 0}><Search size={14} />{submitting ? "Starting search…" : "Search and analyze"}</button>
        <p className="research-form-foot">Searches at most {languages.length * perLanguageLimit} articles. A publisher page may be unavailable or paywalled; its feed excerpt will be labeled clearly.</p>
      </form>

      <div className="research-results-column">
        <section className="panel research-job-panel" aria-live="polite">
          <div className="panel-header"><div><h2 className="panel-title">Search progress</h2><p className="panel-subtitle">Your query is collected and analyzed as one research sample</p></div>{activeJob && <span className={`job-state ${activeJob.status}`}><span />{activeJob.status}</span>}</div>
          {!activeJob ? <div className="research-idle"><div className="research-idle-mark"><Sparkles size={18} /></div><h3>Start with a topic</h3><p>Choose a date range and language to find and compare real coverage.</p></div> : <div className="research-job-content">
            <div className="job-query"><span className="eyebrow">{activeJob.status === "completed" ? "COMPLETED QUERY" : "ACTIVE QUERY"}</span><strong>{activeRequest?.query || `Search job ${activeJob.id}`}</strong><span>{activeRequest?.from_date} — {activeRequest?.to_date} · {(activeRequest?.languages || []).map(languageName).join(", ")}</span></div>
            {activeJob.status === "running" || activeJob.status === "queued" ? <><div className="progress-track"><div className="progress-fill" style={{ width: `${Math.max(4, activeJob.progress)}%` }} /></div><div className="progress-caption"><span>{activeJob.metadata.phase || "Working"}</span><strong>{activeJob.progress}%</strong></div><div className="job-step-line"><LoaderCircle size={14} className="spin-icon" /> Searching feeds, checking source pages, and processing evidence</div></> : null}
            {activeJob.status === "failed" && <div className="error-state">{activeJob.error || "The search could not be completed."}</div>}
            {activeJob.status === "completed" && result && <>
              <div className="research-stat-grid"><ResearchStat label="New articles" value={result.created} /><ResearchStat label="Duplicates" value={result.duplicates} /><ResearchStat label="Story groups" value={result.stories_created} /></div>
              <div className="capture-line"><span className="capture-full">{result.full_text_count} publisher pages captured</span><span className="capture-dot">·</span><span>{result.excerpt_count} feed excerpts</span></div>
              {!!result.warnings.length && <details className="research-warnings"><summary>{result.warnings.length} collection note{result.warnings.length === 1 ? "" : "s"}</summary><ul>{result.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></details>}
            </>}
          </div>}
        </section>

        {activeJob?.status === "completed" && <>
          <section className="research-result-section"><div className="section-head"><div><h2>Stories to compare</h2><p>Clusters contain articles collected by this search.</p></div><span className="panel-kicker">{resultStatus === "loaded" ? `${stories.length} GROUPS` : resultStatus === "failed" ? "UNAVAILABLE" : "LOADING"}</span></div>
            {resultStatus === "loaded" && stories.length ? <div className="research-story-list">{stories.map((story) => <Link className="research-story-row" key={story.id} href={`/stories/${story.id}`}><span className="research-story-icon"><Sparkles size={15} /></span><span className="research-story-copy"><strong>{story.canonical_title}</strong><small>{story.article_count} articles · {story.sources.length} outlets · {story.languages.map(languageName).join(", ")}</small></span><ArrowUpRight size={14} /></Link>)}</div> : <div className="empty-state">{emptyResultsMessage}</div>}
          </section>
          <section className="research-result-section"><div className="section-head"><div><h2>Collected articles</h2><p>Open a source record to review its text, evidence, and provenance.</p></div><span className="panel-kicker">{resultStatus === "loaded" ? `${articles.length} RECORDS` : resultStatus === "failed" ? "UNAVAILABLE" : "LOADING"}</span></div>
            {resultStatus === "loaded" && articles.length ? <div className="article-list research-article-list">{articles.map((article) => <div className="research-article-row" key={article.id}><Link href={`/articles/${article.id}`} className="research-article-copy"><strong>{article.title}</strong><small>{article.source.name} · {languageName(article.language)} · {formatDate(article.published_at)}</small></Link><span className={`content-kind ${article.content_kind === "feed_excerpt" ? "excerpt" : "full"}`}>{article.content_kind === "feed_excerpt" ? "FEED EXCERPT" : "PAGE TEXT"}</span><a aria-label={`Open provider or source result for ${article.title}`} href={article.url} target="_blank" rel="noreferrer" className="source-open"><ExternalLink size={13} /></a></div>)}</div> : <div className="empty-state">{resultStatus === "loaded" ? "No new article records to display." : emptyResultsMessage}</div>}
          </section>
          <p className="page-footer-note">Stored records come from the feeds and source pages returned for this search. Story similarities and article analysis are model inferences for research review, not verified findings.</p>
        </>}

        <section className="research-history-section"><div className="section-head"><div><h2>Recent searches</h2><p>Open a previous collection job.</p></div><span className="panel-kicker">{visibleHistory.length} JOBS</span></div>
          {visibleHistory.length ? <div className="research-history-list">{visibleHistory.slice(0, 8).map((job) => <button type="button" className={`history-row ${job.id === activeJobId ? "selected" : ""}`} key={job.id} onClick={() => { setActiveJobId(job.id); setActiveJob(job); setError(""); }}><span className={`history-status ${job.status}`} /><span className="history-copy"><strong>{job.metadata.request?.query || `Search ${job.id}`}</strong><small>{job.metadata.request?.from_date || ""} · {job.metadata.request?.languages?.map(languageName).join(", ") || ""}</small></span><span className="history-result">{job.status === "completed" ? `${job.metadata.result?.created ?? 0} new` : job.status}</span></button>)}</div> : <div className="history-empty">Your completed search jobs will appear here.</div>}
        </section>
      </div>
    </div>
  </>;
}

function ResearchStat({ label, value }: { label: string; value: number }) {
  return <div className="research-stat"><span>{label}</span><strong>{value}</strong></div>;
}
