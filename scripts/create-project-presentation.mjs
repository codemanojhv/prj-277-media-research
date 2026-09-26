import pptxgen from "pptxgenjs";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "PRJ_277 project team";
pptx.subject = "University prototype for evidence-linked, multilingual news coverage research";
pptx.title = "PRJ_277 | 360-Degree News Coverage Research";
pptx.company = "University project";
pptx.lang = "en-IN";
pptx.theme = {
  headFontFace: "Georgia",
  bodyFontFace: "Aptos",
  lang: "en-IN",
};
if (process.env.PRESENTATION_NO_MASTER !== "1") pptx.defineSlideMaster({
  title: "BASE",
  background: { color: "F7F5EF" },
  objects: [
    { rect: { x: 0.42, y: 7.19, w: 0.24, h: 0.07, line: { color: "E7A54A", transparency: 100 }, fill: { color: "E7A54A" } } },
    { text: { text: "PRJ_277  /  MEDIA RESEARCH", options: { x: 0.78, y: 7.12, w: 4.4, h: 0.19, fontFace: "Aptos", fontSize: 8.5, color: "71817A", charSpacing: 1.2, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.1, w: 0.5, h: 0.2, color: "71817A", fontFace: "Aptos", fontSize: 9, margin: 0, align: "right" },
});

const W = 13.333, H = 7.5;
const C = {
  forest: "173D35", forest2: "21584A", green: "2E8069", mint: "B7D4C4",
  paper: "F7F5EF", white: "FFFFFF", ink: "182D2A", muted: "64766E",
  faint: "E8E9E1", line: "D9DFD7", saffron: "E7A54A", orange: "C8734E",
  blue: "5B88A0", lilac: "8A7EAA", paleGreen: "E5EFE8", paleGold: "F7EBD7",
  paleBlue: "E7EEF1", paleRose: "F4E6DF", dark: "112B26",
};
const FONT_HEAD = "Georgia";
const FONT_BODY = "Aptos";

function txt(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x, y, w, h, margin: 0, breakLine: false,
    fontFace: opts.fontFace || FONT_BODY,
    fontSize: opts.fontSize || 14,
    color: opts.color || C.ink,
    bold: opts.bold || false,
    italic: opts.italic || false,
    align: opts.align || "left",
    valign: opts.valign || "mid",
    fit: "shrink",
    paraSpaceAfterPt: 0,
    charSpacing: opts.charSpacing,
    transparency: opts.transparency,
    bullet: opts.bullet,
    breakLine: false,
    ...opts,
  });
}
function shape(slide, x, y, w, h, fill, radius = 0.12, line = null) {
  slide.addShape(radius ? pptx.ShapeType.roundRect : pptx.ShapeType.rect, {
    x, y, w, h, rectRadius: radius,
    line: { color: line || fill, transparency: line ? 0 : 100, width: 0.8 },
    fill: { color: fill },
  });
}
function circle(slide, x, y, d, fill, line = fill) {
  slide.addShape(pptx.ShapeType.ellipse, { x, y, w: d, h: d, line: { color: line, transparency: line === fill ? 100 : 0 }, fill: { color: fill } });
}
function rule(slide, x1, y1, x2, y2, color = C.line, width = 1.1, dash = "solid") {
  slide.addShape(pptx.ShapeType.line, {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    flipH: x2 < x1, flipV: y2 < y1,
    line: { color, width, dashType: dash, beginArrowType: "none", endArrowType: "none" },
  });
}
function pill(slide, label, x, y, w, fill = C.paleGreen, color = C.forest, h = 0.3) {
  shape(slide, x, y, w, h, fill, 0.13);
  txt(slide, label, x + 0.1, y + 0.01, w - 0.2, h - 0.02, { fontSize: 9, bold: true, color, charSpacing: 0.4, align: "center" });
}
function card(slide, x, y, w, h, { fill = C.white, accent = null, border = null } = {}) {
  shape(slide, x, y, w, h, fill, 0.13, border);
  if (accent) shape(slide, x, y + 0.16, 0.055, h - 0.32, accent, 0.02);
}
function header(slide, section, title, sub = "") {
  txt(slide, section.toUpperCase(), 0.58, 0.38, 7.8, 0.23, { fontSize: 9.5, bold: true, color: C.green, charSpacing: 1.6 });
  txt(slide, title, 0.58, 0.74, 12.0, 0.62, { fontFace: FONT_HEAD, fontSize: 30, bold: true, color: C.ink, valign: "mid" });
  if (sub) txt(slide, sub, 0.6, 1.42, 11.8, 0.36, { fontSize: 13.5, color: C.muted, valign: "top" });
}
function notes(slide, text) { slide.addNotes(text); }
function addCircleLabel(slide, label, x, y, color, size = 0.44) {
  circle(slide, x, y, size, color);
  txt(slide, label, x, y + 0.01, size, size - 0.02, { fontSize: 9, color: C.white, bold: true, align: "center" });
}

// 01 — Cover
{
  const s = pptx.addSlide();
  s.background = { color: C.forest };
  shape(s, 8.48, 0, 4.85, 7.5, C.forest2, 0);
  txt(s, "UNIVERSITY PROJECT  /  PRJ_277", 0.72, 0.62, 6.7, 0.28, { fontSize: 10, color: "D3E3D8", bold: true, charSpacing: 1.7 });
  txt(s, "360°", 0.69, 1.34, 3.5, 1.02, { fontFace: FONT_HEAD, fontSize: 53, color: C.saffron, bold: true });
  txt(s, "News coverage\nresearch system", 0.72, 2.32, 7.4, 1.55, { fontFace: FONT_HEAD, fontSize: 37, color: C.white, bold: true, valign: "top", breakLine: false });
  txt(s, "A multilingual workflow to collect, analyze, compare and trace public reporting on Government of India initiatives.", 0.76, 4.15, 6.65, 0.82, { fontSize: 17, color: "DCE8E0", valign: "top", breakLine: false });
  pill(s, "FUNCTIONAL 60% MILESTONE", 0.76, 5.42, 2.65, "D8E8DC", C.forest, 0.36);
  txt(s, "Evidence-linked  ·  Politically neutral  ·  Local-first", 0.76, 6.04, 6.5, 0.35, { fontSize: 12, color: "C2D6C9", charSpacing: 0.25 });

  // The five language streams converge on one candidate story set.
  const nodeX = 11.15, nodeY = 3.42;
  const streams = [
    { y: 1.02, c: C.saffron, l: "EN" }, { y: 2.0, c: "78B9A2", l: "HI" },
    { y: 2.98, c: "E8D4A5", l: "KN" }, { y: 3.96, c: "9FBBD0", l: "TA" },
    { y: 4.94, c: "D6A692", l: "TE" },
  ];
  for (const st of streams) {
    rule(s, 8.98, st.y + 0.17, nodeX - 0.05, nodeY + 0.22, st.c, 2.2);
    circle(s, 8.83, st.y + 0.04, 0.28, st.c);
    txt(s, st.l, 8.84, st.y + 0.08, 0.26, 0.17, { fontSize: 7, color: C.forest, bold: true, align: "center" });
  }
  circle(s, nodeX - 0.2, nodeY - 0.2, 0.78, C.saffron);
  circle(s, nodeX + 0.02, nodeY + 0.02, 0.34, C.white);
  txt(s, "ONE\nSTORY SET", 9.1, 5.87, 3.15, 0.7, { fontSize: 13, color: C.white, bold: true, align: "center", breakLine: false });
  txt(s, "METHOD • PRODUCT • LIMITS", 9.1, 6.73, 3.15, 0.22, { fontSize: 8.5, color: "C2D6C9", charSpacing: 1.2, align: "center" });
  notes(s, "Introduce this as a university research prototype, not a production media-monitoring or fact-checking service. It demonstrates a traceable path from an explicitly scoped news search to article-level evidence. The default corpus is synthetic.");
}

// 02 — At a glance
{
  const s = pptx.addSlide("BASE"); header(s, "01 / Project at a glance", "A working research slice, measured by capability");
  const stats = [
    ["100", "synthetic articles", C.forest], ["5", "supported languages", C.green],
    ["10", "demo story groups", C.orange], ["6 / 10", "capability groups in scope", C.lilac],
  ];
  stats.forEach(([v, l, c], i) => {
    const x = 0.6 + i * 3.1; card(s, x, 1.72, 2.82, 1.48, { accent: c });
    txt(s, v, x + 0.23, 1.88, 2.35, 0.62, { fontFace: FONT_HEAD, fontSize: 35, bold: true, color: c });
    txt(s, l, x + 0.25, 2.58, 2.3, 0.32, { fontSize: 12, color: C.muted, bold: true });
  });
  txt(s, "20 DEMO ARTICLES PER LANGUAGE", 0.62, 3.67, 4.8, 0.25, { fontSize: 10, color: C.green, bold: true, charSpacing: 1.1 });
  const langs = [["English", 20], ["Hindi", 20], ["Kannada", 20], ["Tamil", 20], ["Telugu", 20]];
  langs.forEach(([name, count], i) => {
    const y = 4.05 + i * 0.47;
    txt(s, name, 0.65, y, 1.35, 0.22, { fontSize: 12, color: C.ink, bold: true });
    shape(s, 2.25, y + 0.02, 4.55, 0.17, C.faint, 0.08);
    shape(s, 2.25, y + 0.02, 4.55, 0.17, i % 2 ? C.green : C.forest, 0.08);
    txt(s, String(count), 7.0, y - 0.02, 0.55, 0.24, { fontSize: 11, color: C.muted, bold: true });
  });
  card(s, 8.2, 3.56, 4.44, 2.55, { fill: C.paleGold, accent: C.saffron });
  txt(s, "Read this correctly", 8.52, 3.87, 3.65, 0.34, { fontFace: FONT_HEAD, fontSize: 20, bold: true });
  txt(s, "The 60% figure tracks six working capability groups out of ten. It is a project-scope measure—not a grade, code-completion percentage, or claim of production readiness.", 8.53, 4.38, 3.53, 1.07, { fontSize: 14, color: C.ink, valign: "top", breakLine: false });
  pill(s, "SYNTHETIC DEMO DATA", 8.54, 5.62, 1.86, C.white, C.orange);
  notes(s, "The synthetic seed contains 100 fictional articles, exactly 20 in each supported language, with 10 candidate story groups and corresponding analyses. A separate online search can add real-source records. Synthetic content must not be cited as real reporting.");
}

// 03 — Problem and study questions
{
  const s = pptx.addSlide("BASE"); header(s, "02 / Research problem", "One public initiative can become five different samples");
  txt(s, "What a researcher must connect", 0.65, 1.8, 3.8, 0.28, { fontSize: 11, bold: true, color: C.green, charSpacing: 0.8 });
  const leftItems = [
    ["01", "Discovery", "Which reports are in scope?"],
    ["02", "Comparability", "Are language and outlet samples comparable?"],
    ["03", "Interpretation", "What is reported, and what is inferred?"],
    ["04", "Traceability", "Can each comparison be checked against its sources?"],
  ];
  leftItems.forEach((it, i) => {
    const y = 2.24 + i * 0.89;
    addCircleLabel(s, it[0], 0.7, y, i === 0 ? C.saffron : C.forest, 0.42);
    txt(s, it[1], 1.3, y - 0.02, 2.2, 0.28, { fontSize: 15, bold: true });
    txt(s, it[2], 1.3, y + 0.31, 4.8, 0.33, { fontSize: 12, color: C.muted });
  });
  card(s, 7.15, 1.92, 5.45, 4.5, { fill: C.forest, accent: C.saffron });
  txt(s, "STUDY QUESTION", 7.55, 2.32, 2.5, 0.25, { fontSize: 10, bold: true, color: "CDE2D3", charSpacing: 1.3 });
  txt(s, "How does coverage differ\nacross languages and\nnews sources?", 7.55, 2.82, 4.55, 1.18, { fontFace: FONT_HEAD, fontSize: 22, bold: true, color: C.white, valign: "top", breakLine: false });
  rule(s, 7.55, 4.4, 11.95, 4.4, "5B8576", 0.8);
  txt(s, "The app reports observed sample differences. It does not infer truth, intent, political bias, or outlet quality.", 7.55, 4.72, 4.3, 0.93, { fontSize: 14, color: "DCE8E0", valign: "top", breakLine: false });
  pill(s, "DESCRIPTIVE COMPARISON", 7.55, 5.91, 2.25, "D8E8DC", C.forest);
  notes(s, "Frame the research question narrowly. The system supports exploratory comparison of a selected sample. It does not establish causal media effects or rank publishers.");
}

// 04 — Query definition
{
  const s = pptx.addSlide("BASE"); header(s, "03 / Research query", "Start with the question—not an unbounded crawl", "A researcher defines the topic, aliases, time window, languages and optional outlet sample.");
  card(s, 0.62, 1.92, 7.1, 4.75, { fill: C.white, border: C.line });
  txt(s, "NEW COVERAGE SEARCH", 0.96, 2.22, 4.2, 0.23, { fontSize: 9.5, color: C.green, bold: true, charSpacing: 1.2 });
  txt(s, "Topic or initiative", 0.98, 2.67, 2.1, 0.23, { fontSize: 11, bold: true });
  shape(s, 0.98, 2.98, 6.25, 0.49, C.paper, 0.08, C.line);
  txt(s, "Swachh Bharat Mission", 1.16, 3.08, 5.85, 0.24, { fontSize: 13, color: C.ink });
  txt(s, "Alternate names", 0.98, 3.68, 1.7, 0.23, { fontSize: 11, bold: true });
  shape(s, 0.98, 3.99, 6.25, 0.55, C.paper, 0.08, C.line);
  txt(s, "Clean India campaign  ·  SBM", 1.16, 4.13, 5.85, 0.24, { fontSize: 12.5, color: C.muted });
  txt(s, "PUBLICATION DATES", 0.98, 4.8, 1.8, 0.2, { fontSize: 9, bold: true, color: C.muted, charSpacing: 0.6 });
  pill(s, "FROM  01 AUG 2026", 0.98, 5.14, 1.82, C.paleBlue, C.blue, 0.36);
  pill(s, "THROUGH  31 AUG 2026", 2.98, 5.14, 2.08, C.paleBlue, C.blue, 0.36);
  txt(s, "LANGUAGE SAMPLE", 0.98, 5.74, 1.8, 0.2, { fontSize: 9, bold: true, color: C.muted, charSpacing: 0.6 });
  ["EN", "HI", "KN", "TA", "TE"].forEach((v, i) => pill(s, v, 0.98 + i * 0.69, 6.06, 0.53, i === 0 ? C.forest : C.paleGreen, i === 0 ? C.white : C.forest, 0.34));
  card(s, 8.05, 1.92, 4.56, 4.75, { fill: C.paleGreen, accent: C.green });
  txt(s, "A bounded online sample", 8.42, 2.28, 3.8, 0.35, { fontFace: FONT_HEAD, fontSize: 20, bold: true });
  const qs = ["Google News RSS + Bing News RSS", "Selected dates and languages", "Optional source-domain filter", "Small per-language result cap"];
  qs.forEach((v, i) => {
    circle(s, 8.43, 2.97 + i * 0.58, 0.17, i === 0 ? C.saffron : C.green);
    txt(s, v, 8.76, 2.94 + i * 0.58, 3.33, 0.25, { fontSize: 12, color: C.ink, bold: i === 0 });
  });
  shape(s, 8.42, 5.47, 3.72, 0.76, C.white, 0.11);
  txt(s, "Not exhaustive", 8.62, 5.61, 1.5, 0.22, { fontSize: 11, color: C.orange, bold: true });
  txt(s, "Search providers and publisher access limit recall.", 8.62, 5.9, 3.2, 0.2, { fontSize: 10, color: C.muted });
  notes(s, "Walk through the query form. Topic and alternate phrases define discovery; date limits use dates reported by feeds; language and outlet restrictions narrow the sample. The collector does not crawl all online media.");
}

// 05 — Flow
{
  const s = pptx.addSlide("BASE"); header(s, "04 / End-to-end workflow", "From search prompt to inspectable comparison", "Every processing stage writes records that downstream screens can trace.");
  const steps = [
    ["01", "DISCOVER", "News feeds, RSS, URL, JSON / CSV", C.saffron],
    ["02", "NORMALIZE", "Text, language, dates, source, hash", C.green],
    ["03", "ANALYZE", "Relevance, tone, stance, topics, evidence", C.blue],
    ["04", "GROUP", "Candidate story set + article links", C.lilac],
    ["05", "COMPARE", "Shared topics, sample differences", C.orange],
    ["06", "TRACE", "Article → evidence → source URL", C.forest],
  ];
  const sx = 0.73, gap = 2.07;
  steps.forEach((v, i) => {
    const x = sx + i * gap;
    if (i < steps.length - 1) rule(s, x + 0.76, 3.07, x + gap - 0.13, 3.07, C.line, 2.2);
    circle(s, x + 0.14, 2.53, 0.9, v[3]);
    txt(s, v[0], x + 0.14, 2.77, 0.9, 0.3, { fontFace: FONT_HEAD, fontSize: 17, color: C.white, bold: true, align: "center" });
    txt(s, v[1], x - 0.15, 3.68, 1.52, 0.23, { fontSize: 10, bold: true, color: v[3], charSpacing: 0.6, align: "center" });
    txt(s, v[2], x - 0.35, 4.07, 1.9, 0.76, { fontSize: 12, color: C.ink, align: "center", valign: "top", breakLine: false });
  });
  card(s, 1.1, 5.49, 11.13, 0.82, { fill: C.paleGold, accent: C.saffron });
  txt(s, "Human review stays in the loop", 1.42, 5.69, 2.72, 0.27, { fontSize: 13, bold: true, color: C.forest });
  txt(s, "Low support stays uncertain; comparison statements link to the article IDs behind them.", 4.05, 5.67, 7.65, 0.31, { fontSize: 13, color: C.ink });
  notes(s, "Describe how each stage produces or enriches stored records. This architecture is intentionally modular: collection, decision provider, similarity/grouping, persistence and UI can evolve separately.");
}

// 06 — Architecture
{
  const s = pptx.addSlide("BASE"); header(s, "05 / Architecture", "Two runtimes, one evidence-first product model");
  card(s, 0.65, 1.8, 5.82, 4.77, { fill: C.white, border: C.line });
  pill(s, "LOCAL DEMO", 0.97, 2.11, 1.32, C.paleGreen, C.forest);
  txt(s, "Next.js dashboard", 0.98, 2.68, 2.4, 0.3, { fontSize: 16, bold: true });
  txt(s, "FastAPI", 0.98, 3.36, 2.4, 0.3, { fontSize: 16, bold: true });
  txt(s, "SQLite", 0.98, 4.04, 2.4, 0.3, { fontSize: 16, bold: true });
  txt(s, "Local rules + multilingual FastEmbed", 0.98, 4.72, 4.75, 0.3, { fontSize: 14, bold: true, color: C.green });
  ["UI", "API", "DB", "MODEL"].forEach((v, i) => {
    const y = 2.61 + i * 0.68;
    pill(s, v, 4.94, y, 0.91, i === 3 ? C.paleGold : C.paleBlue, i === 3 ? C.orange : C.blue, 0.34);
  });
  rule(s, 3.2, 2.91, 4.82, 2.91, C.line, 1.6);
  rule(s, 3.2, 3.59, 4.82, 3.59, C.line, 1.6);
  rule(s, 3.2, 4.27, 4.82, 4.27, C.line, 1.6);
  rule(s, 3.2, 4.95, 4.82, 4.95, C.line, 1.6);

  card(s, 6.85, 1.8, 5.82, 4.77, { fill: C.forest, accent: C.saffron });
  pill(s, "CLOUDFLARE WORKERS", 7.17, 2.11, 2.12, "D8E8DC", C.forest);
  txt(s, "Next.js + OpenNext", 7.2, 2.68, 3.2, 0.3, { fontSize: 16, bold: true, color: C.white });
  txt(s, "Worker API routes", 7.2, 3.36, 3.2, 0.3, { fontSize: 16, bold: true, color: C.white });
  txt(s, "Cloudflare D1", 7.2, 4.04, 3.2, 0.3, { fontSize: 16, bold: true, color: C.white });
  txt(s, "Edge evidence rules + optional TypeSafe JEV", 7.2, 4.72, 4.8, 0.3, { fontSize: 13.5, bold: true, color: "C8DDD0" });
  ["UI", "API", "DB", "JEV*"].forEach((v, i) => {
    const y = 2.61 + i * 0.68;
    pill(s, v, 11.11, y, 1.13, i === 3 ? "654E34" : "D8E8DC", i === 3 ? "FFE5BB" : C.forest, 0.34);
  });
  rule(s, 9.65, 2.91, 10.98, 2.91, "5D8878", 1.6);
  rule(s, 9.65, 3.59, 10.98, 3.59, "5D8878", 1.6);
  rule(s, 9.65, 4.27, 10.98, 4.27, "5D8878", 1.6);
  rule(s, 9.65, 4.95, 10.98, 4.95, "5D8878", 1.6);
  txt(s, "*JEV activates only when the server-side TypeSafe secret is configured. No key is needed for the local baseline or synthetic demo.", 0.86, 6.77, 11.7, 0.23, { fontSize: 10.5, color: C.muted, italic: true });
  notes(s, "The original local demo has FastAPI, SQLite, and a replaceable multilingual embedding provider. The Cloudflare-hosted route is an edge-compatible adapter backed by D1; it uses a lightweight local evidence baseline and can call TypeSafe JEV for decision fields when a secret is configured. The two runtime-specific clustering methods should not be described as identical.");
}

// 07 — Collection and provenance
{
  const s = pptx.addSlide("BASE"); header(s, "06 / Collection and provenance", "Collection is a sample with a chain of custody", "Each article retains enough metadata to explain where it came from and how it entered the study.");
  const sources = [
    ["NEWS SEARCH", "Google News RSS\nBing News RSS", C.saffron],
    ["USER INPUT", "RSS feed\nPublic article URL", C.green],
    ["BULK INPUT", "UTF-8 JSON\nCSV dataset", C.blue],
  ];
  sources.forEach((it, i) => {
    const x = 0.7 + i * 2.08;
    card(s, x, 2.12, 1.84, 1.35, { fill: C.white, border: C.line, accent: it[2] });
    txt(s, it[0], x + 0.2, 2.35, 1.5, 0.2, { fontSize: 9, bold: true, color: it[2], charSpacing: 0.6 });
    txt(s, it[1], x + 0.2, 2.68, 1.45, 0.56, { fontSize: 12, bold: true, valign: "top", breakLine: false });
    rule(s, x + 0.92, 3.56, 7.15, 4.11, C.line, 1.35);
  });
  card(s, 6.1, 3.78, 2.12, 0.98, { fill: C.forest, accent: C.saffron });
  txt(s, "INGEST +\nNORMALIZE", 6.34, 4.01, 1.62, 0.55, { fontSize: 13, color: C.white, bold: true, align: "center", breakLine: false });
  rule(s, 8.31, 4.27, 9.06, 4.27, C.green, 2.2);
  const record = ["Source + domain", "Original URL + discovery URL", "Raw + cleaned content", "Published / collected timestamps", "Content hash + job ID", "Synthetic / excerpt labels"];
  card(s, 9.12, 1.93, 3.52, 4.4, { fill: C.paleGreen, accent: C.green });
  txt(s, "STORED ARTICLE RECORD", 9.47, 2.25, 2.8, 0.24, { fontSize: 9.5, color: C.forest, bold: true, charSpacing: 1 });
  record.forEach((v, i) => {
    circle(s, 9.49, 2.78 + i * 0.52, 0.13, i === 1 ? C.saffron : C.green);
    txt(s, v, 9.78, 2.75 + i * 0.52, 2.47, 0.24, { fontSize: 11.5, color: C.ink, bold: i === 1 });
  });
  pill(s, "DUPLICATES SKIPPED", 0.86, 5.56, 2.01, C.paleGold, C.orange);
  txt(s, "URL or normalized title/content hash", 3.1, 5.58, 3.3, 0.25, { fontSize: 12, color: C.muted });
  notes(s, "Explain that imported and searched articles keep the source URL, discovery URL, timestamps, hash and collection method. Publisher pages may block access; the system stores a labeled provider excerpt rather than claiming full-text capture.");
}

// 08 — Language and relevance
{
  const s = pptx.addSlide("BASE"); header(s, "07 / Language and relevance", "Language is script-detected; relevance is reason-coded", "The demo supports English, Hindi, Kannada, Tamil and Telugu, with a configurable Government of India threshold.");
  const lang = [["EN", "English", C.forest], ["HI", "Hindi", C.green], ["KN", "Kannada", C.orange], ["TA", "Tamil", C.blue], ["TE", "Telugu", C.lilac]];
  lang.forEach((v, i) => {
    const x = 0.75 + i * 1.54;
    circle(s, x + 0.23, 2.1, 0.72, v[2]);
    txt(s, v[0], x + 0.23, 2.31, 0.72, 0.26, { fontSize: 12, bold: true, color: C.white, align: "center" });
    txt(s, v[1], x, 2.99, 1.18, 0.23, { fontSize: 12, bold: true, color: C.ink, align: "center" });
  });
  rule(s, 0.96, 3.59, 7.1, 3.59, C.line, 1.5);
  card(s, 0.77, 4.14, 5.75, 1.68, { fill: C.paleBlue, accent: C.blue });
  txt(s, "Language confidence", 1.11, 4.42, 2.4, 0.29, { fontFace: FONT_HEAD, fontSize: 17, bold: true });
  txt(s, "Script evidence score—not a calibrated probability. Short text, transliteration and code-switching can confuse detection.", 1.12, 4.9, 4.95, 0.62, { fontSize: 12.5, color: C.muted, valign: "top", breakLine: false });
  card(s, 6.86, 4.14, 5.69, 1.68, { fill: C.paleGold, accent: C.saffron });
  txt(s, "Government relevance", 7.2, 4.42, 2.8, 0.29, { fontFace: FONT_HEAD, fontSize: 17, bold: true });
  txt(s, "Multilingual phrase cues + score + matched reasons. The score supports review; it is not a truth probability.", 7.2, 4.9, 4.93, 0.62, { fontSize: 12.5, color: C.muted, valign: "top", breakLine: false });
  pill(s, "DEFAULT RELEVANCE THRESHOLD  0.55", 0.8, 6.18, 2.97, C.paleGreen, C.forest);
  txt(s, "Review false matches and missed coverage before drawing conclusions.", 4.03, 6.2, 5.9, 0.25, { fontSize: 11.5, color: C.muted, italic: true });
  notes(s, "Language detection uses Unicode script ranges and an English Latin-script baseline. GoI relevance is generated from configurable multilingual phrase indicators; both systems return supporting details but have known miss and false match risks.");
}

// 09 — JEV
{
  const s = pptx.addSlide("BASE"); header(s, "08 / TypeSafe AI JEV", "Use JEV for bounded decisions—not as a source of evidence", "Optional structured classifications for collected, non-synthetic articles; local text evidence remains separate.");
  card(s, 0.66, 1.91, 5.42, 4.55, { fill: C.forest, accent: C.saffron });
  pill(s, "OPTIONAL MODEL PROVIDER", 1.02, 2.25, 2.12, "D8E8DC", C.forest);
  txt(s, "TypeSafe AI\nJEV", 1.03, 2.83, 3.75, 1.08, { fontFace: FONT_HEAD, fontSize: 30, color: C.white, bold: true, valign: "top", breakLine: false });
  txt(s, "Structured choices + probabilities", 1.04, 4.14, 4.14, 0.28, { fontSize: 14, color: "DDE9E2", bold: true });
  ["GoI relevance", "Sentiment", "Target-specific stance", "Primary topic"].forEach((v, i) => {
    pill(s, v, 1.04 + (i % 2) * 1.93, 4.7 + Math.floor(i / 2) * 0.49, 1.71, i === 0 ? C.saffron : "D8E8DC", i === 0 ? C.forest : C.forest, 0.34);
  });
  txt(s, "Never sends synthetic demo records", 1.05, 5.91, 4.3, 0.27, { fontSize: 11.5, color: "DDE9E2", bold: true });

  const items = [
    ["01", "Key stays server-side", "Set TYPESAFE_API_KEY as a Cloudflare Worker secret. Never expose it in browser code."],
    ["02", "Gate low confidence", "Low support maps to uncertain / unclear; stance is used only when a policy target is present."],
    ["03", "Keep evidence distinct", "JEV returns decisions, not quote-level rationale. Local snippets and summaries stay separate."],
    ["04", "Review the article", "Probabilities are model outputs—not verified facts or calibrated certainty."],
  ];
  items.forEach((v, i) => {
    const y = 2.08 + i * 1.02;
    addCircleLabel(s, v[0], 6.65, y, i === 0 ? C.saffron : C.green, 0.39);
    txt(s, v[1], 7.2, y - 0.01, 4.4, 0.27, { fontSize: 13.5, bold: true });
    txt(s, v[2], 7.2, y + 0.34, 5.25, 0.53, { fontSize: 11.5, color: C.muted, valign: "top", breakLine: false });
  });
  notes(s, "Explain that JEV has been integrated as an optional provider in both the local API and the Cloudflare edge adapter. The app uses local evidence unless TypeSafe credentials are installed. No API key was supplied during deployment, so the hosted demo uses its local evidence baseline. Gemini and OpenRouter keys do not authenticate to the TypeSafe API.");
}

// 10 — Sentiment and stance
{
  const s = pptx.addSlide("BASE"); header(s, "09 / Interpretation", "Sentiment and policy stance answer different questions");
  txt(s, "OVERALL TONE", 0.73, 1.95, 1.35, 0.23, { fontSize: 9, bold: true, color: C.muted, charSpacing: 1 });
  txt(s, "FAVORABLE", 0.76, 2.5, 1.08, 0.22, { fontSize: 9.5, bold: true, color: C.green });
  txt(s, "CRITICAL", 0.76, 5.39, 1.08, 0.22, { fontSize: 9.5, bold: true, color: C.orange });
  const mx = 2.15, my = 2.18, cw = 4.65, ch = 1.71;
  const cells = [
    [mx, my, C.paleGreen, "POSITIVE TONE  /  SUPPORTIVE STANCE", "Reports benefits and supports the specified policy."],
    [mx + cw + 0.15, my, C.paleBlue, "POSITIVE TONE  /  CRITICAL STANCE", "Notes a benefit while questioning design or delivery."],
    [mx, my + ch + 0.15, C.paleGold, "NEGATIVE TONE  /  SUPPORTIVE STANCE", "Supports the goal but reports a setback or delay."],
    [mx + cw + 0.15, my + ch + 0.15, C.paleRose, "NEGATIVE TONE  /  CRITICAL STANCE", "Criticizes both results and the policy approach."],
  ];
  cells.forEach((v, i) => {
    card(s, v[0], v[1], cw, ch, { fill: v[2], accent: [C.green, C.blue, C.saffron, C.orange][i] });
    txt(s, v[3], v[0] + 0.25, v[1] + 0.25, cw - 0.48, 0.25, { fontSize: 9.3, bold: true, color: [C.green, C.blue, C.orange, C.orange][i], charSpacing: 0.2 });
    txt(s, v[4], v[0] + 0.25, v[1] + 0.72, cw - 0.55, 0.57, { fontSize: 13, color: C.ink, valign: "top", breakLine: false });
  });
  shape(s, 11.85, 2.2, 0.07, 3.6, C.forest, 0.03);
  txt(s, "STANCE TARGET", 10.05, 6.08, 2.0, 0.2, { fontSize: 9, bold: true, color: C.green, charSpacing: 0.8, align: "right" });
  txt(s, "Union Government policy / action", 8.9, 6.38, 3.15, 0.28, { fontSize: 12, bold: true, align: "right" });
  notes(s, "Use the matrix to show why sentiment should not be treated as political stance. A report about a delay may have negative tone yet remain supportive of the policy goal. The actual app scores these fields separately and uses unclear/uncertain when evidence is weak.");
}

// 11 — Evidence model
{
  const s = pptx.addSlide("BASE"); header(s, "10 / Article analysis", "Store the interpretation next to its support");
  const columns = [
    { x: 0.72, label: "ARTICLE TEXT", tag: "INPUT", fill: C.paleBlue, color: C.blue, body: "Title + cleaned content\nSource, date, language\nRaw version retained" },
    { x: 4.74, label: "ANALYSIS", tag: "DECISIONS", fill: C.paleGreen, color: C.green, body: "Summary + key points\nSentiment + stance\nTopics, entities, claims\nConcerns + positive aspects" },
    { x: 8.77, label: "EVIDENCE", tag: "TRACE", fill: C.paleGold, color: C.orange, body: "Supporting text snippets\nConfidence + model label\nTimestamp + provider note\nSource URL + article ID" },
  ];
  columns.forEach((v, i) => {
    card(s, v.x, 2.14, 3.72, 3.49, { fill: v.fill, accent: v.color });
    pill(s, v.tag, v.x + 0.27, 2.45, 1.05, C.white, v.color);
    txt(s, v.label, v.x + 0.27, 2.98, 3.06, 0.36, { fontFace: FONT_HEAD, fontSize: 19, bold: true });
    txt(s, v.body, v.x + 0.28, 3.56, 3.06, 1.54, { fontSize: 13, color: C.ink, valign: "top", breakLine: false, lineSpacingMultiple: 1.1 });
    if (i < 2) {
      rule(s, v.x + 3.79, 3.86, v.x + 4.0, 3.86, C.forest, 2);
      txt(s, "→", v.x + 3.82, 3.69, 0.3, 0.34, { fontSize: 20, bold: true, color: C.forest, align: "center" });
    }
  });
  card(s, 1.12, 5.96, 11.04, 0.58, { fill: C.forest, accent: C.saffron });
  txt(s, "Review rule", 1.43, 6.12, 1.25, 0.22, { fontSize: 11.5, bold: true, color: C.white });
  txt(s, "Model output is an interpretation. Read the full article and inspect the snippet before using it.", 2.8, 6.11, 8.75, 0.24, { fontSize: 12, color: "E4EEE6" });
  notes(s, "At article detail, present analysis fields with evidence and provenance. The local analysis baseline is extractive and rule-supported. JEV returns structured classes but no quote-level explanation; the UI should not imply that a provider decision itself is the evidence.");
}

// 12 — Clustering
{
  const s = pptx.addSlide("BASE"); header(s, "11 / Story intelligence", "Grouping is useful only when its method is visible", "Story comparisons aggregate a selected set of linked article records; clustering quality depends on runtime and sample size.");
  card(s, 0.7, 1.96, 5.76, 3.9, { fill: C.white, border: C.line });
  pill(s, "LOCAL PYTHON DEMO", 1.02, 2.25, 1.85, C.paleGreen, C.forest);
  txt(s, "Multilingual embeddings", 1.04, 2.82, 4.65, 0.38, { fontFace: FONT_HEAD, fontSize: 21, bold: true });
  txt(s, "FastEmbed vectors → cosine similarity → candidate story clusters", 1.05, 3.37, 4.73, 0.62, { fontSize: 14, color: C.ink, valign: "top", breakLine: false });
  rule(s, 1.05, 4.24, 5.83, 4.24, C.line, 1);
  txt(s, "If the model cannot load, the local pipeline logs a lexical fallback.", 1.05, 4.55, 4.75, 0.65, { fontSize: 12.5, color: C.muted, valign: "top", breakLine: false });
  pill(s, "PROVIDER IS REPLACEABLE", 1.05, 5.4, 2.2, C.paleBlue, C.blue);
  card(s, 6.85, 1.96, 5.76, 3.9, { fill: C.forest, accent: C.saffron });
  pill(s, "CLOUDFLARE WORKER", 7.18, 2.25, 1.95, "D8E8DC", C.forest);
  txt(s, "Query-scoped candidate set", 7.19, 2.82, 4.74, 0.38, { fontFace: FONT_HEAD, fontSize: 21, bold: true, color: C.white });
  txt(s, "Online results are collected into a research-job group so their coverage can be compared together.", 7.2, 3.37, 4.74, 0.75, { fontSize: 13.7, color: "E1ECE5", valign: "top", breakLine: false });
  rule(s, 7.2, 4.36, 11.99, 4.36, "5B8576", 1);
  txt(s, "This is a candidate comparison set, not a semantic embedding cluster. Verify event identity before treating reports as the same story.", 7.2, 4.63, 4.72, 0.77, { fontSize: 12.2, color: "D7E6DC", valign: "top", breakLine: false });
  pill(s, "METHOD DIFFERENCE IS EXPLICIT", 7.2, 5.47, 2.7, "D8E8DC", C.forest);
  notes(s, "Keep the difference explicit. The full local baseline uses a multilingual embedding model with a deterministic lexical fallback. The Workers research route presently groups results by submitted research job for comparison and stores those items as a candidate story group. It is not performing the same embedding clustering as the local pipeline; this is a known hosted-prototype limitation.");
}

// 13 — Comparison
{
  const s = pptx.addSlide("BASE"); header(s, "12 / Coverage comparison", "Compare what the stored sample contains", "The analysis is descriptive and links every aggregate back to the article IDs behind it.");
  const langs = [
    ["ENGLISH", 5, C.forest], ["HINDI", 4, C.green], ["KANNADA", 4, C.blue], ["TAMIL", 3, C.orange], ["TELUGU", 4, C.lilac],
  ];
  txt(s, "SAMPLE ARTICLES BY LANGUAGE", 0.8, 1.98, 4.4, 0.23, { fontSize: 9.5, color: C.green, bold: true, charSpacing: 1 });
  langs.forEach((v, i) => {
    const y = 2.45 + i * 0.64;
    txt(s, v[0], 0.8, y, 1.3, 0.22, { fontSize: 10, bold: true, color: C.ink });
    shape(s, 2.2, y + 0.02, 3.32, 0.18, C.faint, 0.08);
    shape(s, 2.2, y + 0.02, v[1] * 0.57, 0.18, v[2], 0.08);
    txt(s, String(v[1]), 5.68, y - 0.01, 0.45, 0.23, { fontSize: 11, bold: true, color: C.muted });
  });
  card(s, 6.52, 1.95, 6.06, 3.71, { fill: C.paleGreen, accent: C.green });
  txt(s, "COMPARISON OUTPUTS", 6.91, 2.28, 3.1, 0.23, { fontSize: 9.5, color: C.green, bold: true, charSpacing: 1 });
  const outputs = [
    ["Shared", "Topics and named entities across reports"],
    ["By language", "Sample size, sources, tone and topics"],
    ["By source", "Observed coverage fields for each outlet"],
    ["Differences", "Observed topic emphasis and group counts"],
  ];
  outputs.forEach((v, i) => {
    const y = 2.76 + i * 0.62;
    circle(s, 6.93, y + 0.03, 0.16, [C.saffron, C.green, C.blue, C.orange][i]);
    txt(s, v[0], 7.25, y, 1.15, 0.22, { fontSize: 12.5, bold: true });
    txt(s, v[1], 8.52, y, 3.46, 0.28, { fontSize: 11.5, color: C.muted });
  });
  card(s, 0.8, 5.83, 11.8, 0.62, { fill: C.paleGold, accent: C.saffron });
  txt(s, "Read with sample sizes", 1.12, 6.02, 2.05, 0.23, { fontSize: 12, bold: true, color: C.orange });
  txt(s, "Language or outlet differences may reflect what was retrieved—not only what was reported.", 3.17, 6.02, 8.8, 0.23, { fontSize: 12, color: C.ink });
  notes(s, "Demonstrate the story detail comparison. Language and source sample sizes are visible; shared topics and differences include article IDs. Do not interpret a small sample as evidence that an outlet is biased or that one language's coverage is representative.");
}

// 14 — User journey
{
  const s = pptx.addSlide("BASE"); header(s, "13 / Product walkthrough", "A student can follow one question all the way to evidence");
  const panels = [
    { x: 0.7, label: "01  OVERVIEW", title: "Start with the stored sample", fill: C.paleGreen, accent: C.green },
    { x: 4.78, label: "02  RESEARCH", title: "Define the query", fill: C.paleBlue, accent: C.blue },
    { x: 8.86, label: "03  ARTICLE", title: "Inspect the record", fill: C.paleGold, accent: C.saffron },
  ];
  panels.forEach((p, i) => {
    card(s, p.x, 2.02, 3.76, 3.95, { fill: p.fill, accent: p.accent });
    txt(s, p.label, p.x + 0.26, 2.31, 2.9, 0.22, { fontSize: 9, color: p.accent, bold: true, charSpacing: 0.8 });
    txt(s, p.title, p.x + 0.26, 2.71, 3.07, 0.55, { fontFace: FONT_HEAD, fontSize: 18, bold: true, valign: "top", breakLine: false });
    if (i === 0) {
      // Minimal editable dashboard wireframe.
      [0, 1, 2].forEach((n) => { shape(s, p.x + 0.28 + n * 1.02, 3.48, 0.86, 0.58, C.white, 0.07); shape(s, p.x + 0.38 + n * 1.02, 3.62, 0.48, 0.09, n === 1 ? C.saffron : C.green, 0.04); shape(s, p.x + 0.38 + n * 1.02, 3.82, 0.63, 0.07, C.faint, 0.04); });
      shape(s, p.x + 0.28, 4.28, 3.15, 0.88, C.white, 0.08);
      [0, 1, 2, 3].forEach((n) => shape(s, p.x + 0.45 + n * 0.6, 4.52, 0.34, 0.36 + (n % 2) * 0.18, [C.green, C.saffron, C.blue, C.lilac][n], 0.06));
    } else if (i === 1) {
      ["TOPIC / INITIATIVE", "DATE RANGE", "LANGUAGE SAMPLE", "OPTIONAL OUTLETS"].forEach((v, n) => {
        txt(s, v, p.x + 0.31, 3.42 + n * 0.47, 1.65, 0.17, { fontSize: 8, bold: true, color: C.muted, charSpacing: 0.5 });
        shape(s, p.x + 1.85, 3.4 + n * 0.47, 1.36, 0.24, C.white, 0.05);
      });
      pill(s, "SEARCH + ANALYZE", p.x + 0.33, 5.43, 1.7, C.forest, C.white, 0.33);
    } else {
      txt(s, "Synthetic article", p.x + 0.3, 3.46, 2.7, 0.2, { fontSize: 9, color: C.orange, bold: true });
      txt(s, "Source, published date, language", p.x + 0.3, 3.8, 3.05, 0.22, { fontSize: 10, color: C.muted });
      shape(s, p.x + 0.3, 4.16, 3.13, 0.58, C.white, 0.07);
      txt(s, "Evidence snippet from stored text…", p.x + 0.47, 4.32, 2.83, 0.22, { fontSize: 10, color: C.ink, italic: true });
      pill(s, "OPEN SOURCE URL", p.x + 0.3, 5.17, 1.64, C.white, C.forest, 0.32);
    }
  });
  rule(s, 4.48, 3.93, 4.67, 3.93, C.forest, 2);
  txt(s, "→", 4.43, 3.75, 0.28, 0.3, { fontSize: 20, color: C.forest, bold: true, align: "center" });
  rule(s, 8.56, 3.93, 8.75, 3.93, C.forest, 2);
  txt(s, "→", 8.5, 3.75, 0.28, 0.3, { fontSize: 20, color: C.forest, bold: true, align: "center" });
  txt(s, "Also reachable via Stories → comparison → linked article", 0.8, 6.32, 9.8, 0.27, { fontSize: 12, color: C.muted, italic: true });
  notes(s, "Use the wireframe to narrate the browser journey. The actual app has dashboard, research, stories, articles and methodology routes. From a completed job, the user can open its candidate story set and inspect the source-level article records.");
}

// 15 — Deployment
{
  const s = pptx.addSlide("BASE"); header(s, "14 / Cloud deployment", "Hosted as a small Workers + D1 prototype");
  const y = 2.49;
  const blocks = [
    ["VISITOR", "Browser", 0.85, 1.72, C.paleBlue, C.blue],
    ["WEB", "Next.js\nOpenNext", 3.15, 2.18, C.paleGreen, C.green],
    ["API", "Worker route\n/ api/*", 6.14, 2.18, C.paleGold, C.orange],
    ["STORE", "Cloudflare\nD1", 9.16, 2.18, C.forest, C.saffron],
  ];
  blocks.forEach((v, i) => {
    card(s, v[2], y, v[3], 1.56, { fill: v[4], accent: v[5] });
    txt(s, v[0], v[2] + 0.22, y + 0.22, v[3] - 0.42, 0.2, { fontSize: 9, bold: true, color: i === 3 ? "FFF0D4" : v[5], charSpacing: 1 });
    txt(s, v[1], v[2] + 0.22, y + 0.62, v[3] - 0.42, 0.58, { fontFace: FONT_HEAD, fontSize: 17, bold: true, color: i === 3 ? C.white : C.ink, valign: "top", breakLine: false });
  });
  [[2.6, 3.0], [5.38, 6.0], [8.36, 9.0]].forEach((p) => {
    rule(s, p[0], y + 0.76, p[1], y + 0.76, C.forest, 2.3);
    txt(s, "→", p[1] - 0.17, y + 0.57, 0.33, 0.32, { fontSize: 20, color: C.forest, bold: true, align: "center" });
  });
  card(s, 0.85, 4.63, 5.46, 1.26, { fill: C.white, border: C.line });
  txt(s, "Demo corpus", 1.16, 4.89, 1.38, 0.25, { fontSize: 13, bold: true });
  txt(s, "100 synthetic records preloaded in D1; no paid model credentials required.", 2.68, 4.85, 3.26, 0.55, { fontSize: 12, color: C.muted, valign: "top", breakLine: false });
  card(s, 6.72, 4.63, 5.7, 1.26, { fill: C.paleGold, accent: C.saffron });
  txt(s, "Optional live JEV", 7.05, 4.89, 1.72, 0.25, { fontSize: 13, bold: true });
  txt(s, "Set a TypeSafe API key as a Worker secret to enable model decisions on real collected articles.", 8.82, 4.85, 3.22, 0.57, { fontSize: 11.5, color: C.muted, valign: "top", breakLine: false });
  txt(s, "A custom domain is optional; the default workers.dev host is sufficient for a class demo.", 0.88, 6.22, 10.6, 0.24, { fontSize: 11.5, color: C.muted, italic: true });
  notes(s, "The app has been adapted to Cloudflare Workers using OpenNext and a D1 database. D1 starts with the synthetic seed and also stores collected public-source records. No TypeSafe secret has been supplied, so the default edge local baseline is active. A custom domain is not necessary for a university demonstration.");
}

// 16 — Verification
{
  const s = pptx.addSlide("BASE"); header(s, "15 / Verification", "Show the artifacts and checks—not only the diagrams");
 const checks = [
    ["100", "synthetic seed articles in D1", C.forest],
    ["101", "stored article analyses", C.green],
    ["11", "candidate story groups incl. live search", C.blue],
    ["5 × 20", "language-balanced demo corpus", C.orange],
  ];
  checks.forEach((v, i) => {
    const x = 0.75 + i * 3.1;
    card(s, x, 1.92, 2.78, 1.43, { fill: C.white, accent: v[2] });
    txt(s, v[0], x + 0.25, 2.1, 2.2, 0.5, { fontFace: FONT_HEAD, fontSize: 28, bold: true, color: v[2] });
    txt(s, v[1], x + 0.25, 2.72, 2.23, 0.35, { fontSize: 11.4, color: C.muted, bold: true });
  });
  card(s, 0.78, 3.82, 7.25, 2.28, { fill: C.paleGreen, accent: C.green });
  txt(s, "Acceptance evidence", 1.12, 4.12, 3.4, 0.32, { fontFace: FONT_HEAD, fontSize: 19, bold: true });
  const accepted = ["API tests cover ingestion, normalization, Unicode, relevance and evidence.", "Live Cloudflare search stored a publisher page with discovery provenance.", "Story and article views expose comparison, evidence and source links."];
  accepted.forEach((v, i) => {
    circle(s, 1.15, 4.7 + i * 0.39, 0.13, C.green);
    txt(s, v, 1.43, 4.67 + i * 0.39, 6.1, 0.28, { fontSize: 11.2, color: C.ink });
  });
  card(s, 8.45, 3.82, 4.12, 2.28, { fill: C.paleGold, accent: C.saffron });
  txt(s, "What is not verified", 8.8, 4.12, 3.25, 0.32, { fontFace: FONT_HEAD, fontSize: 18, bold: true });
  txt(s, "No human-labeled multilingual benchmark; no validation of JEV with a supplied key; no claim of production-grade security or scale.", 8.8, 4.68, 3.1, 0.83, { fontSize: 12.2, color: C.muted, valign: "top", breakLine: false });
  pill(s, "CHECK AT PRESENTATION", 8.8, 5.55, 1.96, C.white, C.orange);
  notes(s, "The D1 row counts were queried from the deployed database after one successful public-source search. API tests and the web type check passed after the relevance-rule update; the Worker was redeployed and the hosted article evidence flow was checked in the browser. The deck intentionally distinguishes prototype checks from model evaluation.");
}

// 17 — Limitations / responsible interpretation
{
  const s = pptx.addSlide("BASE"); header(s, "16 / Limits and responsible interpretation", "Do not confuse a useful workflow with a verified conclusion");
  const rows = [
    ["SAMPLE", "Feed discovery is incomplete; publishers may block pages. Excerpts are labeled."],
    ["LANGUAGE", "Script detection can miss transliteration, code-switching and short text."],
    ["MODEL", "Tone, stance, relevance and topic labels can be wrong; confidence is not correctness."],
    ["CLUSTER", "Local embeddings can split or merge stories; the hosted set is query-scoped."],
    ["COMPARISON", "Different counts may reflect retrieval and sample size, not a real outlet effect."],
  ];
  rows.forEach((v, i) => {
    const y = 1.95 + i * 0.83;
    pill(s, v[0], 0.82, y, 1.32, i === 0 ? C.paleGold : C.paleGreen, i === 0 ? C.orange : C.forest, 0.32);
    txt(s, v[1], 2.44, y + 0.03, 9.55, 0.33, { fontSize: 13, color: C.ink });
    if (i < rows.length - 1) rule(s, 2.44, y + 0.58, 12.03, y + 0.58, C.line, 0.65);
  });
  card(s, 0.84, 6.22, 11.61, 0.55, { fill: C.forest, accent: C.saffron });
  txt(s, "Never use this prototype alone to claim truth, intent, political bias or overall outlet quality.", 1.22, 6.37, 10.7, 0.2, { fontSize: 12.5, color: C.white, bold: true, align: "center" });
  notes(s, "Be direct about the project's limits. Demonstrate provenance and balanced sampling, but do not overstate what a search provider, rule-based field, JEV probability, or small sample can establish. Recommend human annotation and documented sampling criteria for research conclusions.");
}

// 18 — 60 percent and roadmap
{
  const s = pptx.addSlide("BASE"); header(s, "17 / Scope status", "Six capability groups define the completed functional slice");
  const done = [
    "Local foundation + demo dataset", "Ingestion + cleaning + provenance", "Five-language detection + relevance",
    "Article analysis + evidence", "Story comparison workflow", "API + research UI journey",
  ];
  done.forEach((v, i) => {
    const col = i < 3 ? 0 : 1, row = i % 3;
    const x = 0.78 + col * 4.21, y = 1.92 + row * 0.74;
    circle(s, x, y + 0.04, 0.28, C.green);
    txt(s, "✓", x, y + 0.065, 0.28, 0.18, { fontSize: 12, color: C.white, bold: true, align: "center" });
    txt(s, v, x + 0.42, y, 3.43, 0.35, { fontSize: 12.3, bold: true });
  });
  shape(s, 9.06, 1.93, 0.04, 2.42, C.line, 0.02);
  card(s, 9.4, 1.9, 3.13, 2.49, { fill: C.forest, accent: C.saffron });
  txt(s, "6 / 10", 9.78, 2.27, 2.2, 0.67, { fontFace: FONT_HEAD, fontSize: 37, color: C.white, bold: true });
  txt(s, "functional scope", 9.8, 3.02, 2.2, 0.28, { fontSize: 13, color: "D6E5DC", bold: true });
  txt(s, "A scope target, not a rubric score.", 9.8, 3.52, 2.3, 0.48, { fontSize: 11.5, color: "D6E5DC", valign: "top", breakLine: false });
  txt(s, "NEXT", 0.82, 4.58, 1.0, 0.21, { fontSize: 9.5, color: C.orange, bold: true, charSpacing: 1.2 });
  const next = [["07", "Expanded source / language analytics"], ["08", "Global search + researcher cluster review"], ["09", "Retries, scheduling, pipeline controls"], ["10", "Evaluation, release hardening, deployment ops"]];
  next.forEach((v, i) => {
    const x = 0.82 + i * 3.04;
    pill(s, v[0], x, 4.98, 0.5, C.paleGold, C.orange, 0.3);
    txt(s, v[1], x + 0.68, 4.95, 2.13, 0.67, { fontSize: 11.3, color: C.muted, bold: true, valign: "top", breakLine: false });
  });
  notes(s, "The ten equally weighted groups come from the project scope checklist. Groups 1 through 6 comprise the functional 60 percent milestone. The published Cloudflare prototype adds a hosting target, but production hardening, comprehensive evaluation and broader administration remain out of scope.");
}

// 19 — Demo and references
{
  const s = pptx.addSlide(); s.background = { color: C.forest };
  txt(s, "18 / PRESENTATION CLOSE", 0.73, 0.49, 5.8, 0.24, { fontSize: 9.5, color: "D1E2D7", bold: true, charSpacing: 1.5 });
  txt(s, "A clear demo.\nA cautious conclusion.", 0.73, 0.92, 7.1, 1.16, { fontFace: FONT_HEAD, fontSize: 31, color: C.white, bold: true, valign: "top", breakLine: false });
  const demo = [
    "Open Overview and point out the synthetic-data label.",
    "Search one initiative with aliases, a short date range and two languages.",
    "Open the resulting candidate group; compare sample counts and topics.",
    "Open an article; show its evidence snippet, model label and source URL.",
  ];
  demo.forEach((v, i) => {
    addCircleLabel(s, String(i + 1).padStart(2, "0"), 0.82, 2.48 + i * 0.67, i === 0 ? C.saffron : C.green, 0.36);
    txt(s, v, 1.37, 2.49 + i * 0.67, 6.4, 0.31, { fontSize: 12.7, color: "E6EFE8" });
  });
  shape(s, 8.4, 0.52, 4.3, 6.22, C.forest2, 0.16);
  txt(s, "PROJECT REFERENCES", 8.78, 0.91, 3.4, 0.23, { fontSize: 9, color: "D1E2D7", bold: true, charSpacing: 1.2 });
  const refs = [
    ["OpenNext for Cloudflare", "opennext.js.org/cloudflare/get-started"],
    ["Cloudflare Workers", "developers.cloudflare.com/workers/"],
    ["Cloudflare D1", "developers.cloudflare.com/d1/"],
    ["TypeSafe API / JEV", "api.typesafe.ai/docs"],
    ["Project method + limits", "docs/METHODOLOGY.md · docs/LIMITATIONS.md"],
  ];
  refs.forEach((v, i) => {
    const y = 1.42 + i * 0.83;
    txt(s, v[0], 8.78, y, 3.32, 0.24, { fontSize: 12.2, color: C.white, bold: true });
    txt(s, v[1], 8.78, y + 0.32, 3.42, 0.25, { fontSize: 9.8, color: "BCD4C6" });
  });
  rule(s, 8.78, 5.83, 12.27, 5.83, "5C8A78", 0.8);
  txt(s, "Questions", 8.78, 6.07, 2.1, 0.35, { fontFace: FONT_HEAD, fontSize: 20, color: C.saffron, bold: true });
  txt(s, "PRJ_277  ·  360° Media Research", 0.78, 6.87, 5.5, 0.19, { fontSize: 9.2, color: "BED2C5", charSpacing: 0.7 });
  notes(s, "Close by demonstrating the synthetic seed, then a stored public-source search sample from query through article evidence. Answer questions using the documented methodology and limitations. If discussing JEV live classification, explain that it requires a TypeSafe API key and that Gemini/OpenRouter keys are not substitutes. References are vendor documentation and project documentation; the seed is synthetic and live search is a bounded, non-exhaustive sample.");
}

const slideLimit = Number.parseInt(process.env.PRESENTATION_SLIDE_LIMIT || "0", 10);
if (slideLimit > 0 && slideLimit < pptx._slides.length) pptx._slides = pptx._slides.slice(0, slideLimit);
const out = resolve(process.env.PRESENTATION_OUTPUT || "docs/PRJ_277_Project_Presentation.pptx");
await mkdir(dirname(out), { recursive: true });
await pptx.writeFile({ fileName: out });
console.log(`Wrote ${out} (${pptx._slides.length} slides)`);
