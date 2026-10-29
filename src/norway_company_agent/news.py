"""Conservative article metadata extraction; modified dates are never publication dates."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse


def is_news_page(page):
    """Article metadata on home/about/product pages is not a news post."""
    path = urlparse(str(page.get("url") or "")).path
    title = str(page.get("article_title") or "").strip()
    return bool(
        re.search(r"/(?:news|press|press-releases|pressemeldinger|aktuelt|nyheter|artikler|blog|nytt-fra-styret)/[^/]+", path, re.I)
        and page.get("article_type") == "article"
        and title and title.casefold() not in {"news", "nyheter", "aktuelt", "see more news", "les mer", "read more"}
        and page.get("publication_date_source") in {"jsonld.datePublished", "article:published_time"}
        and publication_date(page.get("published_at"))
        and re.fullmatch(r"[a-fA-F0-9]{64}", str(page.get("content_sha256") or ""))
    )


def publication_date(raw):
    if not isinstance(raw, str):
        return None
    try:
        value = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat() if value <= datetime.now(timezone.utc) else None
    except ValueError:
        return None


def article_metadata(soup, url):
    candidates = []

    def walk(node):
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            kinds = node.get("@type", [])
            kinds = kinds if isinstance(kinds, list) else [kinds]
            if set(kinds) & {"Article", "NewsArticle", "BlogPosting", "PressRelease"}:
                candidates.append(node)
            for child in node.values():
                if isinstance(child, (list, dict)):
                    walk(child)

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            walk(json.loads(script.string or script.get_text()))
        except (ValueError, TypeError):
            continue
    target = urlparse(url)._replace(fragment="", query="").geturl().rstrip("/")
    for node in candidates:
        main = node.get("mainEntityOfPage")
        declared = node.get("url") or (main.get("@id") if isinstance(main, dict) else main)
        if declared and urljoin(url, str(declared)).rstrip("/") != target:
            continue
        # Article markup embedded in an archive must identify its own URL.
        if not declared and not soup.select_one("article"):
            continue
        published = publication_date(node.get("datePublished"))
        title = node.get("headline")
        if published and isinstance(title, str) and title.strip():
            return {"article_type": "article", "article_title": title.strip(), "published_at": published, "publication_date_source": "jsonld.datePublished"}
    kind = soup.select_one('meta[property="og:type"][content="article"]')
    date = soup.select_one('meta[property="article:published_time"]')
    heading = soup.select_one("article h1, main h1, h1")
    if kind and date and heading and (published := publication_date(date.get("content"))):
        return {"article_type": "article", "article_title": heading.get_text(" ", strip=True), "published_at": published, "publication_date_source": "article:published_time"}
    return {}
