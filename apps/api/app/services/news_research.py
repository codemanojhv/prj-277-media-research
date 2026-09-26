from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urlparse

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Article
from app.services.ingestion import fetch_article_record, ingest_records
from app.services.language import clean_text, detect_language

LANGUAGE_LOCALES = {
    "en": {"label": "English", "google": ("en-IN", "IN:en"), "bing": "en-in"},
    "hi": {"label": "Hindi", "google": ("hi-IN", "IN:hi"), "bing": "hi-in"},
    "kn": {"label": "Kannada", "google": ("kn-IN", "IN:kn"), "bing": "kn-in"},
    "ta": {"label": "Tamil", "google": ("ta-IN", "IN:ta"), "bing": "ta-in"},
    "te": {"label": "Telugu", "google": ("te-IN", "IN:te"), "bing": "te-in"},
}

OUTLETS = [
    {"id": "the-hindu", "name": "The Hindu", "domains": ["thehindu.com"]},
    {"id": "indian-express", "name": "The Indian Express", "domains": ["indianexpress.com"]},
    {"id": "times-of-india", "name": "The Times of India", "domains": ["timesofindia.indiatimes.com"]},
    {"id": "hindustan-times", "name": "Hindustan Times", "domains": ["hindustantimes.com"]},
    {"id": "ndtv", "name": "NDTV", "domains": ["ndtv.com"]},
    {"id": "india-today", "name": "India Today", "domains": ["indiatoday.in"]},
    {"id": "dd-news", "name": "DD News", "domains": ["ddnews.gov.in"]},
    {"id": "pib", "name": "Press Information Bureau", "domains": ["pib.gov.in"]},
    {"id": "mint", "name": "Mint", "domains": ["livemint.com"]},
    {"id": "economic-times", "name": "The Economic Times", "domains": ["economictimes.indiatimes.com"]},
    {"id": "deccan-herald", "name": "Deccan Herald", "domains": ["deccanherald.com"]},
    {"id": "new-indian-express", "name": "The New Indian Express", "domains": ["newindianexpress.com"]},
]
OUTLET_BY_ID = {outlet["id"]: outlet for outlet in OUTLETS}
MAX_DATE_SPAN_DAYS = 366


@dataclass
class Candidate:
    title: str
    url: str
    discovery_url: str
    source_name: str
    domain: str | None
    published_at: datetime | None
    snippet: str
    language: str
    provider: str


def _clean_term(value: str) -> str:
    return clean_text(re.sub(r"[\x00-\x1f]", " ", value or "").replace('"', " ").replace("'", " "))[:120]


def _date_value(value) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(str(value))
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _publisher_url(link: str) -> str:
    parsed = urlparse(link)
    host = (parsed.hostname or "").lower()
    if host == "bing.com" or host.endswith(".bing.com"):
        wrapped = parse_qs(parsed.query).get("url", [""])[0]
        wrapped_host = (urlparse(wrapped).hostname or "").lower()
        if wrapped_host and not any(
            wrapped_host == root or wrapped_host.endswith(f".{root}")
            for root in ("bing.com", "google.com", "google.co.in")
        ):
            return wrapped
    return link


def _is_provider_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == root or host.endswith(f".{root}") for root in ("google.com", "google.co.in", "bing.com"))


def _candidate_from_entry(entry, language: str, provider: str) -> Candidate | None:
    title = clean_text(str(entry.get("title") or ""))[:500]
    link = str(entry.get("link") or "").strip()
    if not title or not link:
        return None
    direct_url = _publisher_url(link)
    source = entry.get("source") or {}
    source_name = clean_text(str(source.get("title") or ""))
    domain = (urlparse(direct_url).hostname or "").lower().removeprefix("www.") or None
    if domain and _is_provider_url(f"https://{domain}"):
        domain = None
    if domain is None:
        source_host = urlparse(str(source.get("href") or "")).hostname or ""
        domain = source_host.lower().removeprefix("www.") or None
        if domain and _is_provider_url(f"https://{domain}"):
            domain = None
    if not source_name:
        title_parts = re.split(r"\s+[|–—-]\s+", title, maxsplit=1)
        source_name = title_parts[-1] if len(title_parts) > 1 else ""
    if domain is None:
        source_name_key = source_name.casefold()
        known = next((outlet for outlet in OUTLETS if outlet["name"].casefold() == source_name_key), None)
        domain = known["domains"][0] if known else None
    if not source_name:
        known = next((outlet for outlet in OUTLETS if domain in outlet["domains"]), None)
        source_name = known["name"] if known else domain or "Online news source"
    published = entry.get("published") or entry.get("updated")
    published_at = _date_value(published)
    if published_at is None and entry.get("published_parsed"):
        try:
            published_at = datetime(*entry.published_parsed[:6]).replace(tzinfo=UTC)
        except (TypeError, ValueError):
            published_at = None
    snippet = clean_text(str(entry.get("summary") or entry.get("description") or ""))
    text_language, confidence = detect_language(f"{title} {snippet}", language)
    if confidence < 0.4:
        text_language = language
    return Candidate(title, direct_url, link, source_name[:200], domain, published_at, snippet, text_language, provider)


def _google_query(terms: list[str], from_date: date, to_date: date, domains: list[str]) -> str:
    phrase = " OR ".join(f'"{term}"' for term in terms)
    parts = [f"({phrase})", f"after:{from_date.isoformat()}", f"before:{(to_date + timedelta(days=1)).isoformat()}"]
    if domains:
        parts.append("(" + " OR ".join(f"site:{domain}" for domain in domains) + ")")
    return " ".join(parts)


def _bing_query(terms: list[str]) -> str:
    # Bing News RSS does not reliably honor Google-style date/site operators.
    # Apply those constraints locally after discovery to avoid empty feeds.
    return " OR ".join(f'"{term}"' for term in terms)


def _fetch_feed(url: str, params: dict[str, str]) -> list:
    response = httpx.get(
        url,
        params=params,
        timeout=httpx.Timeout(12.0, connect=4.0),
        follow_redirects=True,
        headers={"User-Agent": "PRJ-277-Academic-Research-Demo/0.1"},
    )
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if feed.bozo and not feed.entries:
        raise ValueError("The search provider returned a feed that could not be parsed")
    return feed.entries


def _matches_outlet(candidate: Candidate, domains: list[str]) -> bool:
    if not domains:
        return True
    host = (candidate.domain or "").lower().removeprefix("www.")
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def _normal_title(title: str) -> str:
    return clean_text(re.sub(r"[^\w\s]", " ", title.casefold(), flags=re.UNICODE))


def _in_date_range(candidate: Candidate, from_date: date, to_date: date) -> bool:
    if candidate.published_at is None:
        return False
    return from_date <= candidate.published_at.date() <= to_date


def _search_candidates(
    terms: list[str], from_date: date, to_date: date, languages: list[str], outlet_ids: list[str], progress=None
) -> tuple[list[Candidate], dict[str, int], list[str]]:
    domains = [domain for outlet_id in outlet_ids for domain in OUTLET_BY_ID[outlet_id]["domains"]]
    candidates: list[Candidate] = []
    provider_counts = {"Google News RSS": 0, "Bing News RSS": 0}
    warnings: list[str] = []
    total_steps = max(1, len(languages) * 2)
    step = 0
    for language in languages:
        locale = LANGUAGE_LOCALES[language]
        hl, ceid = locale["google"]
        providers = [
            (
                "Google News RSS",
                "https://news.google.com/rss/search",
                {"q": _google_query(terms, from_date, to_date, domains), "hl": hl, "gl": "IN", "ceid": ceid},
            ),
            (
                "Bing News RSS",
                "https://www.bing.com/news/search",
                {"q": _bing_query(terms), "format": "rss", "setlang": locale["bing"]},
            ),
        ]
        for provider, url, params in providers:
            step += 1
            try:
                entries = _fetch_feed(url, params)
                for entry in entries:
                    candidate = _candidate_from_entry(entry, language, provider)
                    if candidate:
                        candidates.append(candidate)
                        provider_counts[provider] += 1
            except (httpx.HTTPError, OSError, ValueError) as exc:
                warnings.append(f"{provider} ({LANGUAGE_LOCALES[language]['label']}): {type(exc).__name__}: {exc}")
            if progress:
                progress(10 + round(step * 25 / total_steps), f"Searching {LANGUAGE_LOCALES[language]['label']} coverage")

    filtered: list[Candidate] = []
    seen_urls: set[str] = set()
    seen_titles: set[tuple[str, str]] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            int(not _is_provider_url(item.url)),
            item.published_at.timestamp() if item.published_at else 0,
        ),
        reverse=True,
    ):
        if candidate.language not in languages:
            continue
        if not _in_date_range(candidate, from_date, to_date):
            continue
        if not _matches_outlet(candidate, domains):
            continue
        normalized_url = candidate.url.split("#", 1)[0].rstrip("/").casefold()
        title_key = (_normal_title(candidate.title), candidate.domain or candidate.source_name.casefold())
        if normalized_url in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(normalized_url)
        seen_titles.add(title_key)
        filtered.append(candidate)
    return filtered, provider_counts, warnings


def collect_online_coverage(
    db: Session,
    *,
    query: str,
    aliases: list[str],
    from_date: date,
    to_date: date,
    languages: list[str],
    outlet_ids: list[str],
    per_language_limit: int,
    job_id: int,
    progress=None,
) -> dict:
    terms = list(dict.fromkeys(term for term in (_clean_term(query), *(_clean_term(value) for value in aliases)) if term))
    candidates, provider_counts, warnings = _search_candidates(
        terms, from_date, to_date, languages, outlet_ids, progress
    )
    counts = {language: 0 for language in languages}
    selected: list[Candidate] = []
    for candidate in candidates:
        if counts[candidate.language] >= per_language_limit:
            continue
        selected.append(candidate)
        counts[candidate.language] += 1

    def capture(candidate: Candidate) -> tuple[dict | None, str | None]:
        try:
            host = (urlparse(candidate.url).hostname or "").lower()
            if any(host == root or host.endswith(f".{root}") for root in ("google.com", "google.co.in", "bing.com")):
                raise ValueError("Search provider link does not expose a direct publisher page")
            record = fetch_article_record(candidate.url)
            if len(clean_text(str(record.get("content") or ""))) < 20:
                raise ValueError("Publisher page did not contain enough readable article text")
            record["source_name"] = candidate.source_name
            record["domain"] = candidate.domain or record.get("domain")
            record["collection_method"] = "online_search"
            record["content_kind"] = "article_page"
            return record, None
        except Exception as exc:
            if len(candidate.snippet) < 20:
                return None, f"Could not capture {candidate.url}: {type(exc).__name__}: {exc}; no usable feed excerpt"
            return {
                "url": candidate.url,
                "discovery_url": candidate.discovery_url,
                "title": candidate.title,
                "raw_content": candidate.snippet,
                "content": candidate.snippet,
                "published_at": candidate.published_at,
                "source_name": candidate.source_name,
                "domain": candidate.domain,
                "language": candidate.language,
                "collection_method": "online_search",
                "content_kind": "feed_excerpt",
            }, None

    captured: list[tuple[dict | None, str | None] | None] = [None] * len(selected)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(capture, candidate): index for index, candidate in enumerate(selected)}
        for completed, future in enumerate(as_completed(futures), start=1):
            captured[futures[future]] = future.result()
            if progress:
                progress(35 + round(completed * 20 / max(1, len(selected))), f"Capturing article {completed} of {len(selected)}")

    records: list[dict] = []
    for candidate, capture_result in zip(selected, captured, strict=True):
        if capture_result is None:
            continue
        record, warning = capture_result
        if warning:
            warnings.append(warning)
        if record is None:
            continue
        record["title"] = candidate.title or record.get("title")
        record["published_at"] = candidate.published_at or record.get("published_at")
        record["language"] = candidate.language
        record["discovery_url"] = candidate.discovery_url
        record["search_query"] = " | ".join(terms)
        record["research_job_id"] = job_id
        record["source_type"] = "online_news"
        records.append(record)

    result = ingest_records(db, records)
    warnings.extend(result.pop("errors", []))
    stored = list(db.scalars(select(Article).where(Article.id.in_(result["article_ids"])))) if result["article_ids"] else []
    full_text_count = sum(article.content_kind == "article_page" for article in stored)
    excerpt_count = sum(article.content_kind == "feed_excerpt" for article in stored)
    result.update({
        "query": query,
        "aliases": aliases,
        "date_range": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "languages": languages,
        "outlet_ids": outlet_ids,
        "provider_counts": provider_counts,
        "full_text_count": full_text_count,
        "excerpt_count": excerpt_count,
        "warnings": warnings[:30],
        "language_counts": counts,
    })
    return result
