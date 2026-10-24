"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Activity, Clock3, Database, Plus, RefreshCw, Rss, Trash2 } from "lucide-react";
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, type SourceRecord } from "@/lib/api";

type Schedule = { enabled: boolean; interval_minutes: number; next_run_at: string | null };
type Job = { id: number; job_type: string; status: string; progress: number; started_at: string | null; completed_at: string | null; error: string | null; metadata: Record<string, unknown> };
const languageChoices = [["en", "English"], ["hi", "Hindi"], ["kn", "Kannada"], ["ta", "Tamil"], ["te", "Telugu"]];

function displayTime(value: string | null) {
  if (!value) return "Not scheduled";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Not scheduled" : new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export default function OperationsPage() {
  const hosted = process.env.NEXT_PUBLIC_DEPLOYMENT_LABEL?.includes("CLOUDFLARE") || false;
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [schedule, setSchedule] = useState<Schedule>({ enabled: false, interval_minutes: 1440, next_run_at: null });
  const [name, setName] = useState("");
  const [rssUrl, setRssUrl] = useState("");
  const [language, setLanguage] = useState("en");
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const [sourceData, jobData, scheduleData] = await Promise.all([
        apiGet<{ items: SourceRecord[] }>("/sources"),
        apiGet<{ items: Job[] }>("/pipeline/jobs?limit=50"),
        apiGet<Schedule>("/pipeline/schedule"),
      ]);
      setSources(sourceData.items);
      setJobs(jobData.items);
      setSchedule(scheduleData);
      setError("");
    } catch (issue) { setError(issue instanceof Error ? issue.message : "Could not load operations data."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (hosted) return;
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [load, hosted]);

  async function run(path: string, label: string) {
    setRunning(true);
    setError("");
    setMessage("");
    try {
      const job = await apiPost<{ id: number; status: string }>(path);
      setMessage(`${label} queued as job ${job.id}.`);
      await load();
    } catch (issue) { setError(issue instanceof Error ? issue.message : "The operation could not be started."); }
    finally { setRunning(false); }
  }

  async function addSource(event: FormEvent) {
    event.preventDefault();
    setRunning(true);
    setError("");
    setMessage("");
    try {
      await apiPost("/sources", { name: name.trim(), rss_url: rssUrl.trim(), language, is_active: true });
      setName("");
      setRssUrl("");
      setMessage("RSS source added and enabled for scheduled collection.");
      await load();
    } catch (issue) { setError(issue instanceof Error ? issue.message : "The RSS source could not be added."); }
    finally { setRunning(false); }
  }

  async function toggleSource(source: SourceRecord) {
    try {
      await apiPatch(`/sources/${source.id}`, { is_active: !source.is_active });
      await load();
    } catch (issue) { setError(issue instanceof Error ? issue.message : "The source setting could not be changed."); }
  }

  async function saveSource(event: FormEvent<HTMLFormElement>, source: SourceRecord) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const rss = String(values.get("rss_url") || "").trim();
    try {
      await apiPatch(`/sources/${source.id}`, {
        name: String(values.get("name") || "").trim(),
        rss_url: rss || null,
        language: String(values.get("language") || source.language),
        region: String(values.get("region") || "").trim() || null,
      });
      setMessage(`${source.name} settings saved.`);
      await load();
    } catch (issue) { setError(issue instanceof Error ? issue.message : "Source settings could not be saved."); }
  }

  async function removeSource(source: SourceRecord) {
    try {
      await apiDelete(`/sources/${source.id}`);
      setMessage(`${source.name} was removed.`);
      await load();
    } catch (issue) { setError(issue instanceof Error ? issue.message : "The source could not be removed."); }
  }

  async function saveSchedule(event: FormEvent) {
    event.preventDefault();
    try {
      const saved = await apiPut<Schedule>("/pipeline/schedule", schedule);
      setSchedule(saved);
      setMessage(saved.enabled ? `Feed collection is scheduled. Next run: ${displayTime(saved.next_run_at)}.` : "Scheduled collection is paused.");
      setError("");
    } catch (issue) { setError(issue instanceof Error ? issue.message : "The schedule could not be saved."); }
  }

  async function retry(job: Job) {
    try {
      const retried = await apiPost<{ id: number }>(`/pipeline/jobs/${job.id}/retry`);
      setMessage(`Retry queued as job ${retried.id}.`);
      await load();
    } catch (issue) { setError(issue instanceof Error ? issue.message : "This job could not be retried."); }
  }

  const activeJobs = jobs.filter((job) => job.status === "queued" || job.status === "running").length;

  if (hosted) return <><div className="page-heading-row"><div><p className="eyebrow">HOSTED PROTOTYPE</p><h1 className="page-title">Operations controls</h1><p className="page-lede">Source management, scheduled collection, retries, and full-corpus reanalysis run in the local FastAPI workflow.</p></div></div><div className="note-box">The Cloudflare demo supports stored-sample analytics and lexical corpus search. Its public operations controls stay disabled until hosted write access is protected.</div></>;

  return <>
    <div className="page-heading-row"><div><p className="eyebrow">LOCAL WORKFLOW / FEED + JOB CONTROL</p><h1 className="page-title">Operations</h1><p className="page-lede">Manage RSS inputs, schedule collection, run analysis, and recover failed processing jobs.</p></div><div className="heading-meta"><strong>{activeJobs} ACTIVE JOBS</strong>Background work in progress</div></div>
    {error && <div className="error-state" role="alert">{error}</div>}{message && <div className="success-state" role="status">{message}</div>}
    <div className="operations-grid">
      <section className="panel operations-panel"><div className="section-head"><div><h2><Activity size={16} /> Run the pipeline</h2><p>Reanalyze stored articles or collect from enabled feeds.</p></div></div><div className="operation-actions"><button className="btn-primary" type="button" disabled={running} onClick={() => void run("/pipeline/run", "Full analysis") }><RefreshCw size={14} /> Reanalyze all records</button><button className="btn-secondary" type="button" disabled={running} onClick={() => void run("/pipeline/collect-sources", "Feed collection")}><Rss size={14} /> Collect enabled feeds</button></div><p className="page-footer-note">Analysis refreshes local evidence and candidate clusters. Manually curated story groups are retained.</p></section>
      <form className="panel operations-panel" onSubmit={saveSchedule}><div className="section-head"><div><h2><Clock3 size={16} /> Collection schedule</h2><p>Recurring feed collection runs while the local API is running.</p></div></div><label className="schedule-toggle"><input type="checkbox" checked={schedule.enabled} onChange={(event) => setSchedule((current) => ({ ...current, enabled: event.target.checked }))} /><span>Enable scheduled collection</span></label><label className="field-label" htmlFor="schedule-interval">Run every<select id="schedule-interval" className="filter-select" value={schedule.interval_minutes} onChange={(event) => setSchedule((current) => ({ ...current, interval_minutes: Number(event.target.value) }))}><option value={60}>1 hour</option><option value={360}>6 hours</option><option value={720}>12 hours</option><option value={1440}>24 hours</option><option value={10080}>7 days</option></select></label><div className="schedule-next">Next run: <strong>{displayTime(schedule.next_run_at)}</strong></div><button className="btn-primary" type="submit">Save schedule</button></form>
      <section className="panel operations-panel"><div className="section-head"><div><h2><Plus size={16} /> Add an RSS source</h2><p>Only enabled sources with a feed URL are collected.</p></div></div><form className="source-create-form" onSubmit={addSource}><label className="field-label">Source name<input className="filter-input" required minLength={2} maxLength={200} value={name} onChange={(event) => setName(event.target.value)} /></label><label className="field-label">RSS or Atom URL<input className="filter-input" type="url" required value={rssUrl} onChange={(event) => setRssUrl(event.target.value)} placeholder="https://publisher.example/feed.xml" /></label><label className="field-label">Primary language<select className="filter-select" value={language} onChange={(event) => setLanguage(event.target.value)}>{languageChoices.map(([code, label]) => <option value={code} key={code}>{label}</option>)}</select></label><button className="btn-primary" disabled={running} type="submit">Add feed source</button></form></section>
      <section className="panel operations-panel"><div className="section-head"><div><h2><Database size={16} /> Source registry</h2><p>{sources.length} stored sources · {sources.filter((source) => source.rss_url && source.is_active).length} active feeds</p></div></div><div className="source-registry">{sources.map((source) => <div className="source-registry-row" key={source.id}><div><strong>{source.name}</strong><span>{source.rss_url || "No feed URL"}</span><small>{source.article_count} articles · {source.language.toUpperCase()}{source.region ? ` · ${source.region}` : ""}</small><details className="source-edit"><summary>Configure source</summary><form onSubmit={(event) => void saveSource(event, source)}><label>Name<input name="name" defaultValue={source.name} required minLength={2} maxLength={200} /></label><label>RSS URL<input name="rss_url" type="url" defaultValue={source.rss_url || ""} placeholder="Optional until scheduling" /></label><label>Language<select name="language" defaultValue={source.language}>{languageChoices.map(([code, label]) => <option value={code} key={code}>{label}</option>)}</select></label><label>Region<input name="region" defaultValue={source.region || ""} maxLength={120} /></label><button className="btn-secondary" type="submit">Save source</button></form></details></div><label className="source-enabled"><input type="checkbox" checked={source.is_active} disabled={!source.rss_url} onChange={() => void toggleSource(source)} /><span>{source.is_active ? "Enabled" : "Paused"}</span></label>{source.article_count === 0 && <button className="icon-button" type="button" aria-label={`Delete ${source.name}`} onClick={() => void removeSource(source)}><Trash2 size={14} /></button>}</div>)}{!sources.length && <div className="empty-state">No sources are registered yet.</div>}</div></section>
      <section className="panel operations-panel operations-jobs"><div className="section-head"><div><h2><Activity size={16} /> Recent jobs</h2><p>Failed jobs can be retried with their saved request.</p></div><button className="text-link" type="button" onClick={() => void load()}>Refresh</button></div>{loading ? <div className="loading-state">Loading recent operations…</div> : jobs.length ? <div className="job-list">{jobs.map((job) => <article className="job-row" key={job.id}><div className={`job-status-dot ${job.status}`} /><div className="job-copy"><strong>#{job.id} · {job.job_type.replaceAll("-", " ")}</strong><span>{job.status} · {job.progress}%{job.started_at ? ` · started ${displayTime(job.started_at)}` : ""}</span>{job.error && <small>{job.error}</small>}</div>{job.status === "failed" && <button className="btn-secondary" type="button" onClick={() => void retry(job)}>Retry</button>}</article>)}</div> : <div className="empty-state">No processing jobs have run.</div>}</section>
    </div>
  </>;
}
