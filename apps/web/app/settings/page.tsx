"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Copy, KeyRound, RefreshCw, ShieldCheck } from "lucide-react";
import { apiGet, type AnalysisProviderStatus } from "@/lib/api";

function KeyStatus({ ready }: { ready?: boolean }) {
  return <span className={`badge ${ready ? "positive" : "mixed"}`}>{ready ? "Configured" : "Not configured"}</span>;
}

function CopyCommand({ value, children }: { value: string; children: string }) {
  const [copied, setCopied] = useState(false);
  return <button className="btn-secondary" type="button" onClick={async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }}>{copied ? <Check size={14} /> : <Copy size={14} />}{copied ? "Copied" : children}</button>;
}

export default function ProviderSettingsPage() {
  const [status, setStatus] = useState<AnalysisProviderStatus | null>(null);
  const [error, setError] = useState("");
  const refresh = useCallback(() => {
    setError("");
    return apiGet<AnalysisProviderStatus>("/analysis/provider").then(setStatus).catch((issue) => setError(issue instanceof Error ? issue.message : "Provider status is unavailable."));
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  return <>
    <div className="page-heading"><div><span className="eyebrow">CONFIGURATION</span><h1>Provider keys</h1><p>Check which research providers are configured for this deployment.</p></div><button className="btn-secondary" type="button" onClick={() => { void refresh(); }}><RefreshCw size={14} /> Refresh status</button></div>
    {error && <div className="error-state" role="alert">{error}</div>}
    <section className="panel detail-section">
      <div className="section-head"><div><h2>Provider status</h2><p>Only configured/not configured status is shown; key values are never returned.</p></div><ShieldCheck size={18} /></div>
      <div className="article-list">
        <div className="settings-provider-row"><div><strong>AI analysis · {status?.display_name || "Checking…"}</strong><small>Structured article decisions</small></div><KeyStatus ready={status?.api_key_configured} /></div>
        <div className="settings-provider-row"><div><strong>LLM summaries · {status?.text_generation?.display_name || "Checking…"}</strong><small>Evidence-linked summary generation</small></div><KeyStatus ready={status?.text_generation?.api_key_configured} /></div>
        <div className="settings-provider-row"><div><strong>Social comments · {status?.social_reactions?.display_name || "Checking…"}</strong><small>Reddit comments through Scrape Creators</small></div><KeyStatus ready={status?.social_reactions?.api_key_configured} /></div>
      </div>
    </section>
    <section className="panel detail-section">
      <div className="section-head"><div><h2>Set or rotate a key</h2><p>Keys are server-side secrets. This page does not accept or save secret values.</p></div><KeyRound size={18} /></div>
      <details className="settings-details" open>
        <summary>Cloudflare deployment</summary>
        <p>Run these commands from the project folder in a trusted terminal. Wrangler prompts for each value without putting it in the command or source code.</p>
        <div className="settings-command"><code>cd apps/web; npx wrangler secret put GEMINI_API_KEY</code><CopyCommand value="cd apps/web; npx wrangler secret put GEMINI_API_KEY">Copy Gemini command</CopyCommand></div>
        <div className="settings-command"><code>cd apps/web; npx wrangler secret put TYPESAFE_API_KEY</code><CopyCommand value="cd apps/web; npx wrangler secret put TYPESAFE_API_KEY">Copy JEV command</CopyCommand></div>
        <div className="settings-command"><code>cd apps/web; npx wrangler secret put SCRAPECREATORS_API_KEY</code><CopyCommand value="cd apps/web; npx wrangler secret put SCRAPECREATORS_API_KEY">Copy Scrape Creators command</CopyCommand></div>
        <p className="count-mono">Wrangler deploys a new Worker version when a secret is changed. Local keys are separate.</p>
      </details>
      <details className="settings-details">
        <summary>Local demo</summary>
        <p>Set keys in the root <code>.env</code> file, then restart <code>npm run demo</code>. Use an editor on your machine; do not paste secret values into this page, D1, or source control.</p>
        <pre className="settings-env">GEMINI_API_KEY=your_gemini_key{"\n"}TYPESAFE_API_KEY=your_typesafe_key{"\n"}SCRAPECREATORS_API_KEY=your_scrape_creators_key</pre>
      </details>
      <div className="note-box">Scrape Creators currently adds Reddit comment search to public reaction analysis. Each scan makes one comment-search request; review the provider’s current credit usage before running many scans. Reactions are a platform-limited sample, not representative public opinion.</div>
    </section>
  </>;
}
