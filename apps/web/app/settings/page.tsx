"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Copy, KeyRound, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { apiGet, type AnalysisProviderStatus } from "@/lib/api";
import { readUserProviderSettings, writeUserProviderSettings } from "@/lib/user-provider-settings";

const MODELS = [
  { id: "gemini-3.8-flash", label: "Gemini 3.8 Flash · Fast" },
  { id: "gemini-3.7-flash", label: "Gemini 3.7 Flash · Balanced" },
  { id: "gemini-3.5-flash", label: "Gemini 3.5 Flash · Fast" },
  { id: "gemini-3.5-flash-lite", label: "Gemini 3.5 Flash-Lite · Lightweight" },
  { id: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
  { id: "gemini-2.5-pro", label: "Gemini 2.5 Pro · Advanced" },
];
const CUSTOM_MODEL = "custom";

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
  const [notice, setNotice] = useState("");
  const [modelChoice, setModelChoice] = useState(MODELS[0].id);
  const [customModel, setCustomModel] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [scrapeKey, setScrapeKey] = useState("");
  const [hasSessionGeminiKey, setHasSessionGeminiKey] = useState(false);
  const [hasSessionScrapeKey, setHasSessionScrapeKey] = useState(false);

  const refresh = useCallback(() => {
    setError("");
    return apiGet<AnalysisProviderStatus>("/analysis/provider")
      .then(setStatus)
      .catch((issue) => setError(issue instanceof Error ? issue.message : "Provider status is unavailable."));
  }, []);

  useEffect(() => {
    const saved = readUserProviderSettings();
    const isPreset = MODELS.some((model) => model.id === saved.geminiModel);
    setModelChoice(isPreset ? saved.geminiModel : CUSTOM_MODEL);
    if (!isPreset) setCustomModel(saved.geminiModel);
    setHasSessionGeminiKey(Boolean(saved.geminiApiKey));
    setHasSessionScrapeKey(Boolean(saved.scrapeCreatorsApiKey));
    void refresh();
  }, [refresh]);

  function saveGeminiSettings() {
    const model = modelChoice === CUSTOM_MODEL ? customModel.trim() : modelChoice;
    if (!/^[A-Za-z0-9._:/-]{1,120}$/u.test(model)) {
      setError("Choose a listed Gemini model or enter a valid model ID.");
      return;
    }
    const current = readUserProviderSettings();
    const key = geminiKey.trim() || current.geminiApiKey;
    if (geminiKey.trim().length > 4096 || /[\r\n\u0000]/u.test(geminiKey)) {
      setError("That API key is too long or contains unsupported characters.");
      return;
    }
    if (!writeUserProviderSettings({ ...current, geminiModel: model, geminiApiKey: key })) {
      setError("This browser tab does not allow session storage, so the settings could not be saved.");
      return;
    }
    setHasSessionGeminiKey(Boolean(key));
    setGeminiKey("");
    setNotice(key ? `Saved ${model} for this browser tab. Your key is hidden again.` : `Saved ${model}. Add a Gemini API key to use your own account.`);
    setError("");
  }

  function removeGeminiKey() {
    const current = readUserProviderSettings();
    if (!writeUserProviderSettings({ ...current, geminiApiKey: "" })) return;
    setHasSessionGeminiKey(false);
    setGeminiKey("");
    setNotice("Your Gemini key was removed from this tab.");
  }

  function saveScrapeKey() {
    if (!scrapeKey.trim()) {
      setError("Paste a Scrape Creators API key first.");
      return;
    }
    if (scrapeKey.trim().length > 4096 || /[\r\n\u0000]/u.test(scrapeKey)) {
      setError("That API key is too long or contains unsupported characters.");
      return;
    }
    const current = readUserProviderSettings();
    if (!writeUserProviderSettings({ ...current, scrapeCreatorsApiKey: scrapeKey.trim() })) {
      setError("This browser tab does not allow session storage, so the key could not be saved.");
      return;
    }
    setHasSessionScrapeKey(true);
    setScrapeKey("");
    setNotice("Scrape Creators key saved for this browser tab. The key is hidden again.");
    setError("");
  }

  function removeScrapeKey() {
    const current = readUserProviderSettings();
    if (!writeUserProviderSettings({ ...current, scrapeCreatorsApiKey: "" })) return;
    setHasSessionScrapeKey(false);
    setScrapeKey("");
    setNotice("Your Scrape Creators key was removed from this tab.");
  }

  return <>
    <div className="page-heading"><div><span className="eyebrow">CONFIGURATION</span><h1>Provider keys</h1><p>Choose your analysis model and connect your own provider accounts.</p></div><button className="btn-secondary" type="button" onClick={() => { void refresh(); }}><RefreshCw size={14} /> Refresh server status</button></div>
    {error && <div className="error-state" role="alert">{error}</div>}
    {notice && <div className="note-box" role="status">{notice}</div>}

    <section className="panel detail-section">
      <div className="section-head"><div><h2>LLM analysis</h2><p>Choose a Gemini model and enter your own Google AI Studio API key.</p></div><KeyRound size={18} /></div>
      <div className="research-field" style={{ marginBottom: 12 }}>
        <label className="eyebrow" htmlFor="gemini-model">Model</label>
        <select id="gemini-model" className="filter-select" value={modelChoice} onChange={(event) => setModelChoice(event.target.value)}>
          {MODELS.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}
          <option value={CUSTOM_MODEL}>Enter a model ID…</option>
        </select>
        {modelChoice === CUSTOM_MODEL && <input className="filter-input" value={customModel} onChange={(event) => setCustomModel(event.target.value)} placeholder="Gemini model ID" aria-label="Custom Gemini model ID" />}
      </div>
      <div className="research-field">
        <label className="eyebrow" htmlFor="gemini-key">Google Gemini API key</label>
        <input id="gemini-key" className="filter-input" type="password" autoComplete="new-password" maxLength={4096} value={geminiKey} onChange={(event) => setGeminiKey(event.target.value)} placeholder={hasSessionGeminiKey ? "Key saved for this tab; paste a replacement to rotate it" : "Paste your Gemini API key"} />
      </div>
      <div className="research-limit-row" style={{ justifyContent: "flex-start", flexWrap: "wrap" }}>
        <button className="btn-primary" type="button" onClick={saveGeminiSettings}>Save LLM settings</button>
        <KeyStatus ready={hasSessionGeminiKey || status?.text_generation?.api_key_configured} />
        {hasSessionGeminiKey && <button className="btn-secondary" type="button" onClick={removeGeminiKey}><Trash2 size={13} /> Remove my key</button>}
      </div>
      <p className="count-mono">Models are sent to Google’s Gemini API. Check current model availability and billing in <a className="source-link" href="https://ai.google.dev/gemini-api/docs/models" target="_blank" rel="noreferrer">Google’s model list</a>.</p>
    </section>

    <section className="panel detail-section">
      <div className="section-head"><div><h2>Scrape Creators · Reddit</h2><p>Add Reddit comments to public reaction searches with your own account.</p></div><ShieldCheck size={18} /></div>
      <div className="research-field">
        <label className="eyebrow" htmlFor="scrape-key">Scrape Creators API key</label>
        <input id="scrape-key" className="filter-input" type="password" autoComplete="new-password" maxLength={4096} value={scrapeKey} onChange={(event) => setScrapeKey(event.target.value)} placeholder={hasSessionScrapeKey ? "Key saved for this tab; paste a replacement to rotate it" : "Paste your Scrape Creators API key"} />
      </div>
      <div className="research-limit-row" style={{ justifyContent: "flex-start", flexWrap: "wrap" }}>
        <button className="btn-primary" type="button" onClick={saveScrapeKey}>Save Scrape Creators key</button>
        <KeyStatus ready={hasSessionScrapeKey || status?.social_reactions?.api_key_configured} />
        {hasSessionScrapeKey && <button className="btn-secondary" type="button" onClick={removeScrapeKey}><Trash2 size={13} /> Remove my key</button>}
      </div>
      <p className="count-mono">A Reddit comment search uses your Scrape Creators account. Bluesky and Hacker News searches do not need this key.</p>
    </section>

    <section className="panel detail-section">
      <div className="section-head"><div><h2>Shared deployment status</h2><p>These are server-side defaults. Your session keys take priority for your requests.</p></div><ShieldCheck size={18} /></div>
      <div className="article-list">
        <div className="settings-provider-row"><div><strong>Article decisions · {status?.display_name || "Checking…"}</strong><small>Shared TypeSafe JEV configuration</small></div><KeyStatus ready={status?.api_key_configured} /></div>
        <div className="settings-provider-row"><div><strong>LLM summaries · {status?.text_generation?.display_name || "Checking…"}</strong><small>Shared Gemini deployment key</small></div><KeyStatus ready={status?.text_generation?.api_key_configured} /></div>
        <div className="settings-provider-row"><div><strong>Social comments · {status?.social_reactions?.display_name || "Checking…"}</strong><small>Shared Scrape Creators deployment key</small></div><KeyStatus ready={status?.social_reactions?.api_key_configured} /></div>
      </div>
      {status?.message && <p className="count-mono" style={{ marginTop: 12 }}>{status.message}</p>}
      <details className="settings-details">
        <summary>Deployment owner: manage shared Worker keys</summary>
        <p>These commands set shared defaults for the whole deployment. Use the user key fields above for private, tab-only settings.</p>
        <div className="settings-command"><code>cd apps/web; npx wrangler secret put GEMINI_API_KEY</code><CopyCommand value="cd apps/web; npx wrangler secret put GEMINI_API_KEY">Copy Gemini command</CopyCommand></div>
        <div className="settings-command"><code>cd apps/web; npx wrangler secret put SCRAPECREATORS_API_KEY</code><CopyCommand value="cd apps/web; npx wrangler secret put SCRAPECREATORS_API_KEY">Copy Scrape Creators command</CopyCommand></div>
      </details>
      <div className="note-box">Your own keys stay in this browser tab’s session storage, are attached only to requests that use the selected provider, and are not saved in the project database. Closing the tab clears them. “Configured” means a key is saved; its validity is checked when you use that provider. Provider use may incur charges on your account.</div>
    </section>
  </>;
}
