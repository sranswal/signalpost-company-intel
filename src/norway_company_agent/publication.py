"""The public claim boundary: raw candidate snapshots are never published facts."""
from __future__ import annotations

import hashlib
from typing import Any

from .news import is_news_page

STATES = {"available", "not_available", "blocked", "not_applicable", "ambiguous", "failed"}


def availability(record: dict | None, module: str = "") -> str:
    if not record:
        return "failed"
    status = record.get("status")
    if status == "available":
        if module == "website" and not ((record.get("value") or {}).get("identity_assessment") or {}).get("publishable"):
            return "ambiguous"
        if module == "financials" and not (record.get("value") or {}).get("records"):
            return "not_available"
        return "available"
    return {"not_found": "not_available", "blocked": "blocked", "not_applicable": "not_applicable", "ambiguous": "ambiguous"}.get(status, "failed")


def published_claims(profile: dict, modules: list[str]) -> tuple[list[dict], list[dict]]:
    claims, sources = [], []
    for module in modules:
        record = profile.get("evidence", {}).get(module) or {}
        state = availability(record, module)
        evidence_id = hashlib.sha256(f"{profile['organisation_number']}|{module}|{record.get('content_sha256')}|{record.get('source_url')}".encode()).hexdigest()[:24]
        if record:
            sources.append({"id": evidence_id, **record, "availability": state, "snapshot_role": "raw_source_candidate" if module == "website" and state != "available" else "source_snapshot"})

        def add(field, value, **metadata):
            claims.append({"field": field, "value": value, "availability": state, "evidence_ids": [evidence_id] if record else [], **metadata})

        if state != "available":
            add(module, None)
            continue
        value = record.get("value") or {}
        if module == "website":
            add("official_website", value.get("final_url") or record.get("source_url"))
            if value.get("description"):
                add("business_description", value["description"], classification="company_reported")
            assessments = {item.get("url"): item for item in value.get("social_link_assessments", [])}
            for link in value.get("social_links") or []:
                if assessments.get(link.get("url"), {}).get("publishable"):
                    add("social_account", link, ownership_basis="exact_site_outbound_and_full_handle_match")
            for page in value.get("pages") or []:
                if is_news_page(page):
                    page_id = hashlib.sha256(f"{profile['organisation_number']}|{page.get('url')}|{page.get('content_sha256')}".encode()).hexdigest()[:24]
                    sources.append({"id": page_id, "source_url": page.get("url"), "retrieved_at": record.get("retrieved_at"), "content_sha256": page.get("content_sha256"), "claim_span": page.get("article_title"), "source_class": "company_owned_article", "published_at": page["published_at"]})
                    claims.append({"field": "company_news", "value": {"title": page.get("article_title"), "url": page.get("url"), "published_at": page["published_at"]}, "availability": "available", "evidence_ids": [page_id]})
        elif module == "financials":
            for row in value.get("records") or []:
                add("annual_accounts", row, reporting_period=row.get("period"), freshness=value.get("freshness"), scope="legal_entity")
            if value.get("comparison"):
                add("financial_comparison", value["comparison"], ordering="older_to_newer")
            if not value.get("records"):
                claims.append({"field": "annual_accounts", "value": None, "availability": "not_available", "evidence_ids": [evidence_id]})
        else:
            add(module, value)
    return claims, sources
