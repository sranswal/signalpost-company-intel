"""Check saved public artifacts without mistaking internal candidates for claims."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from norway_company_agent.batch import read_organisation_numbers, validate_envelopes
from norway_company_agent.news import is_news_page
from norway_company_agent.refresh import diff_datasets


def validate(manifest, envelopes, profiles):
    expected = read_organisation_numbers(manifest)
    errors = []
    contract = validate_envelopes(envelopes, len(expected))
    if [row["organisation_number"] for row in envelopes] != expected:
        errors.append("Envelope order/membership differs from input")
    if [row["organisation_number"] for row in profiles] != expected:
        errors.append("Profile order/membership differs from input")
    fields = Counter()
    for row in envelopes:
        source_ids = {source["id"] for source in row["evidence"]}
        for claim in row["claims"]:
            if not set(claim["evidence_ids"]) <= source_ids:
                errors.append(f"Unresolved evidence: {row['organisation_number']}/{claim['field']}")
            if claim["availability"] != "available":
                continue
            fields[claim["field"]] += 1
            if not claim["evidence_ids"]:
                errors.append("Published claim lacks evidence")
            for ref in claim["evidence_ids"]:
                source = next(source for source in row["evidence"] if source["id"] == ref)
                if not source.get("source_url") or not source.get("retrieved_at") or not source.get("content_sha256"):
                    errors.append(f"Incomplete provenance: {row['organisation_number']}/{claim['field']}")
            if claim["field"] == "annual_accounts" and claim["value"].get("account_type") == "KONSERN":
                errors.append("Group accounts escaped legal-entity boundary")
            if claim["field"] == "company_news":
                pages = (row.get("profile", {}).get("evidence", {}).get("website", {}).get("value") or {}).get("pages") or []
                if not any(page.get("url") == claim["value"].get("url") and is_news_page(page) for page in pages):
                    errors.append("News claim lacks a dated individual article")
        website = row.get("profile", {}).get("evidence", {}).get("website", {})
        if not (((website.get("value") or {}).get("identity_assessment") or {}).get("publishable")):
            if any(claim["field"] in {"official_website", "social_account", "company_news", "business_description"} and claim["availability"] == "available" for claim in row["claims"]):
                errors.append("Unverified website generated a public claim")
    return {"passed": contract["passed"] and not errors, "contract": contract, "errors": errors, "companies": len(envelopes), "available_claim_counts": dict(fields), "same_snapshot_changes": len(diff_datasets(profiles, profiles)), "freshness": dict(Counter(((row.get("evidence", {}).get("financials", {}).get("value") or {}).get("freshness") or {}).get("status", "unavailable") for row in profiles)), "identity_abstentions": sum(row["modules"].get("website", {}).get("state") == "ambiguous" for row in envelopes), "measurement_boundary": "Structural/provenance checks and same-snapshot replay; not independently labelled real-world precision/recall"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--envelopes", required=True)
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    def read(path):
        return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    report = validate(args.manifest, read(args.envelopes), read(args.profiles))
    report["artifact_sha256"] = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in (args.manifest, args.envelopes, args.profiles)}
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
