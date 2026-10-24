from __future__ import annotations

import csv
import hashlib
import io
import ipaddress
import json
import socket
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Article, Source
from app.services.language import clean_text, detect_language

MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_ARTICLE_CHARS = 160_000


def clean_html(value: str) -> str:
    soup = BeautifulSoup(value or "", "html.parser")
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg"]):
        element.decompose()
    paragraphs = [clean_text(node.get_text(" ", strip=True)) for node in soup.select("article p, main p, p")]
    text = "\n\n".join(paragraph for paragraph in paragraphs if len(paragraph) > 30)
    if not text:
        text = soup.get_text(" ", strip=True)
    return clean_text(text)[:MAX_ARTICLE_CHARS]


def _parse_date(value) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(str(value))
            except (TypeError, ValueError, OverflowError):
                parsed = datetime.now(UTC)
    else:
        parsed = datetime.now(UTC)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _content_hash(title: str, content: str) -> str:
    normalized = f"{clean_text(title).casefold()}\n{clean_text(content).casefold()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_record(record: dict) -> dict:
    title = clean_text(str(record.get("title") or "Untitled article"))[:500]
    raw = record.get("raw_content") or record.get("content") or record.get("body") or record.get("text") or ""
    if isinstance(raw, list):
        raw = " ".join(str(item.get("value", item)) if isinstance(item, dict) else str(item) for item in raw)
    raw = str(raw)
    content = clean_html(raw) if "<" in raw and ">" in raw else clean_text(raw)
    content = content[:MAX_ARTICLE_CHARS]
    if len(content) < 20:
        raise ValueError("Article content must contain at least 20 readable characters")
    url = str(record.get("url") or "").strip()
    if not url:
        url = f"urn:prj277:import:{_content_hash(title, content)}"
    declared_language = str(record.get("language") or "").lower()
    language, confidence = detect_language(f"{title} {content}", declared_language or None)
    source_name = clean_text(str(record.get("source_name") or record.get("source") or "Imported source"))[:200]
    source_domain = str(record.get("domain") or (urlparse(url).hostname if url.startswith(("http://", "https://")) else ""))
    is_synthetic = bool(record.get("is_synthetic", False))
    return {
        "title": title,
        "raw_content": raw[:MAX_ARTICLE_CHARS],
        "clean_content": content,
        "url": url,
        "author": clean_text(str(record.get("author") or ""))[:255] or None,
        "published_at": _parse_date(record.get("published_at") or record.get("date")),
        "language": language,
        "language_confidence": confidence,
        "region": clean_text(str(record.get("region") or ""))[:120] or None,
        "source_name": source_name,
        "domain": source_domain[:255] or None,
        "source_type": str(record.get("source_type") or "news")[:40],
        "rss_url": record.get("rss_url"),
        "is_synthetic": is_synthetic,
        "collection_method": str(record.get("collection_method") or ("synthetic_demo" if is_synthetic else "dataset_upload"))[:40],
        "content_kind": str(record.get("content_kind") or ("synthetic_text" if is_synthetic else "article_page"))[:24],
        "search_query": clean_text(str(record.get("search_query") or ""))[:1000] or None,
        "discovery_url": str(record.get("discovery_url") or "")[:2048] or None,
        "research_job_id": record.get("research_job_id"),
        "content_hash": _content_hash(title, content),
    }


def ingest_records(db: Session, records: list[dict]) -> dict:
    created = duplicates = failed = 0
    errors: list[str] = []
    article_ids: list[int] = []
    for index, raw in enumerate(records):
        try:
            item = normalize_record(raw)
            existing = db.scalar(select(Article.id).where(or_(Article.url == item["url"], Article.content_hash == item["content_hash"])))
            if existing:
                duplicates += 1
                continue
            source = db.scalar(select(Source).where(Source.name == item["source_name"]))
            if source is None:
                source = Source(
                    name=item["source_name"], domain=item["domain"], language=item["language"],
                    region=item["region"], source_type=item["source_type"], rss_url=item["rss_url"],
                )
                db.add(source)
                db.flush()
            article = Article(
                source_id=source.id,
                url=item["url"],
                title=item["title"],
                raw_content=item["raw_content"],
                clean_content=item["clean_content"],
                author=item["author"],
                published_at=item["published_at"],
                language=item["language"],
                language_confidence=item["language_confidence"],
                region=item["region"],
                content_hash=item["content_hash"],
                is_synthetic=item["is_synthetic"],
                collection_method=item["collection_method"],
                content_kind=item["content_kind"],
                search_query=item["search_query"],
                discovery_url=item["discovery_url"],
                research_job_id=item["research_job_id"],
            )
            db.add(article)
            db.flush()
            article_ids.append(article.id)
            created += 1
            if index and index % 50 == 0:
                db.flush()
        except (ValueError, TypeError, UnicodeError) as exc:
            failed += 1
            errors.append(f"row {index + 1}: {exc}")
    db.commit()
    return {"created": created, "duplicates": duplicates, "failed": failed, "errors": errors[:20], "article_ids": article_ids}


def parse_dataset(filename: str, content: bytes) -> list[dict]:
    if len(content) > MAX_IMPORT_BYTES:
        raise ValueError("Dataset exceeds the 5 MB import limit")
    decoded = content.decode("utf-8-sig")
    if filename.lower().endswith(".csv"):
        return list(csv.DictReader(io.StringIO(decoded)))
    value = json.loads(decoded)
    records = value.get("articles", value) if isinstance(value, dict) else value
    if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
        raise ValueError("JSON dataset must be a list of article objects or an object with an 'articles' list")
    return records


def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use a public http or https article/feed URL")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Local and internal network URLs are not allowed")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {ipaddress.ip_address(result[4][0]) for result in socket.getaddrinfo(host, parsed.port or 443)}
        except OSError as exc:
            raise ValueError("The URL host could not be resolved") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Local and private network addresses are not allowed")
    return url


def _get_public_url(url: str) -> httpx.Response:
    current_url = validate_public_url(url)
    for _ in range(6):
        response = httpx.get(
            current_url,
            timeout=httpx.Timeout(8.0, connect=3.0),
            follow_redirects=False,
            headers={"User-Agent": "PRJ-277-Academic-Research-Demo/0.1"},
        )
        location = response.headers.get("location")
        if response.status_code in {301, 302, 303, 307, 308} and location:
            current_url = validate_public_url(urljoin(current_url, location))
            continue
        response.raise_for_status()
        if len(response.content) > MAX_IMPORT_BYTES:
            raise ValueError("Remote content exceeds the 5 MB limit")
        return response
    raise ValueError("The URL redirected too many times")


def fetch_article_record(url: str) -> dict:
    response = _get_public_url(url)
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.find("h1") or soup.title
    title_text = title.get_text(" ", strip=True) if title else "Untitled article"
    author_tag = soup.find("meta", attrs={"name": "author"})
    date_tag = soup.find("meta", attrs={"property": "article:published_time"}) or soup.find("meta", attrs={"name": "date"})
    date_value = date_tag.get("content") if date_tag else None
    paragraphs = soup.select("article p, main p") or soup.select("p")
    body = "\n\n".join(p.get_text(" ", strip=True) for p in paragraphs)
    if not body:
        body = soup.get_text(" ", strip=True)
    final_url = str(response.url)
    host = urlparse(final_url).hostname or "unknown source"
    source_name = host.removeprefix("www.").split(".")[0].replace("-", " ").title()
    return {
        "url": final_url,
        "discovery_url": url if final_url != url else None,
        "title": title_text,
        "raw_content": response.text,
        "content": body,
        "author": author_tag.get("content") if author_tag else None,
        "published_at": date_value,
        "source_name": source_name,
        "domain": host,
        "source_type": "url",
        "collection_method": "manual_url",
        "content_kind": "article_page",
    }


def ingest_url(db: Session, url: str) -> dict:
    return ingest_records(db, [fetch_article_record(url)])


def ingest_rss(db: Session, url: str, max_entries: int = 12, source_name: str | None = None) -> dict:
    feed_response = _get_public_url(url)
    feed = feedparser.parse(feed_response.content)
    if feed.bozo and not feed.entries:
        raise ValueError("The RSS feed could not be parsed")
    feed_title = clean_text(source_name or str(feed.feed.get("title") or urlparse(url).hostname or "RSS source"))[:200]
    records: list[dict] = []
    errors: list[str] = []
    for entry in feed.entries[:max_entries]:
        link = str(entry.get("link") or "").strip()
        if not link:
            continue
        try:
            record = fetch_article_record(link)
            record["source_name"] = feed_title
            record["rss_url"] = url
            record["source_type"] = "rss"
            record["collection_method"] = "rss_feed"
            record["discovery_url"] = link
            record["published_at"] = entry.get("published") or entry.get("updated") or record.get("published_at")
            records.append(record)
        except Exception as exc:
            errors.append(f"{link}: {type(exc).__name__}: {exc}")
            summary = clean_text(BeautifulSoup(str(entry.get("summary", "")), "html.parser").get_text(" ", strip=True))
            if len(summary) >= 20:
                records.append({
                    "url": link, "title": entry.get("title"), "content": summary,
                    "published_at": entry.get("published") or entry.get("updated"),
                    "source_name": feed_title, "rss_url": url, "source_type": "rss",
                    "collection_method": "rss_feed", "content_kind": "feed_excerpt", "discovery_url": link,
                })
    result = ingest_records(db, records)
    result["fetch_errors"] = errors[:10]
    result["feed_title"] = feed_title
    return result
