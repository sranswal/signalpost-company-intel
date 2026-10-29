#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profile_complete_for_modules, profiles_from_bulk, read_organisation_inputs, terminal_envelope, validate_envelopes  # noqa: E402
from norway_company_agent.evidence import utc_now, evidence  # noqa: E402
from norway_company_agent.refresh import diff_profile  # noqa: E402
from norway_company_agent.operations import latency_summary  # noqa: E402
from norway_company_agent.publication import availability  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.official import fetch_official_modules, assess_financial_freshness, accounting_obligation_assessment  # noqa: E402
from norway_company_agent.website import fetch_website  # noqa: E402


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluator-owned Signalpost batch contract")
    parser.add_argument("--organisations", required=True, help="JSON, JSONL, or text organisation-number list")
    parser.add_argument("--bulk", required=True, help="Frozen Brreg entity snapshot")
    parser.add_argument("--output", required=True, help="Terminal envelope JSONL")
    parser.add_argument("--profiles-output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-count", type=int, help="Optional assertion; otherwise use the supplied batch length")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--modules", default="registry,accounting_obligation,registry_live,financials,roles,group,locations,website")
    parser.add_argument("--seeds", help="Optional verified website seeds JSON file")
    parser.add_argument("--previous-profiles", help="Previous profile JSONL; preserve snapshots and report material changes")
    parser.add_argument("--changes-output", help="Material change JSONL (default: changes.jsonl beside --output)")
    args = parser.parse_args()

    started_at = utc_now()
    run_started = time.monotonic()
    organisation_inputs = read_organisation_inputs(args.organisations)
    orgs = [item["organisation_number"] for item in organisation_inputs]
    if args.expected_count is not None and len(orgs) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} organisations, received {len(orgs)}")
    args.expected_count = len(orgs)
    if not orgs or args.workers < 1 or args.checkpoint_every < 1:
        raise SystemExit("Batch must be nonempty and worker/checkpoint counts must be positive")
    profiles, registry_metadata = profiles_from_bulk(args.bulk, orgs)

    seeds_by_org = {}
    if args.seeds and Path(args.seeds).exists():
        raw_seeds = json.loads(Path(args.seeds).read_text(encoding="utf-8"))
        seeds_by_org = {str(item["organisation_number"]): item for item in raw_seeds}

    annotations = {item["organisation_number"]: item for item in organisation_inputs}
    for profile in profiles:
        org = profile["organisation_number"]
        ann = annotations.get(org, {})
        for key in ("evaluation_split", "sample_slice", "website_seed_source", "website_seed_proof"):
            if key in ann:
                profile[key] = ann[key]
        seed = seeds_by_org.get(org) or (ann if ann.get("website_seed_source") else None)
        if not profile.get("website") and seed and seed.get("website"):
            profile["website"] = str(seed["website"]).strip()
            profile["website_seed_source"] = seed.get("website_seed_source", "independently_verified_exact_entity")
            profile["website_seed_proof"] = seed.get("website_seed_proof") or {
                "proof_url": str(seed.get("proof_url") or ""),
                "proof": str(seed.get("proof") or ""),
            }
    requested_modules = [item.strip() for item in args.modules.split(",") if item.strip()]
    supported_modules = {"registry", "accounting_obligation", "registry_live", "financials", "financial_history", "roles", "group", "locations", "website"}
    if not requested_modules or set(requested_modules) - supported_modules:
        raise SystemExit("Specify supported nonempty modules: " + ",".join(sorted(supported_modules)))
    fetch_modules = set(requested_modules) - {"registry", "accounting_obligation", "website"}
    operations = {"requests": 0, "bytes": 0, "latencies_ms": []}

    def enrich(profile: dict) -> tuple[dict, dict]:
        company_started = time.monotonic()
        records, metrics = fetch_official_modules(profile["organisation_number"], fetch_modules)
        profile["evidence"].update(records)
        live_record = records.get("registry_live") or {}
        live_value = live_record.get("value") or {}
        for key in ("name", "legal_form", "website", "latest_submitted_accounts", "employees"):
            if live_value.get(key) is not None:
                profile[key] = live_value[key]
        if live_record.get("status") == "available":
            profile["evidence"]["accounting_obligation"] = accounting_obligation_assessment(profile)
        assess_financial_freshness(profile)
        if live_value.get("deleted") or live_value.get("slettedato"):
            profile["deleted"] = True
            profile["slettedato"] = live_value.get("slettedato")
        website_metrics = {"requests": 0, "bytes": 0, "latencies_ms": []}
        if "website" in requested_modules:
            website_record, website_metrics = fetch_website(profile.get("website"))
            profile["evidence"]["website"] = apply_website_identity_gate(profile, website_record)["website"]
        metric = {
            "requests": sum(item.requests for item in metrics) + website_metrics["requests"],
            "bytes": sum(item.bytes_received for item in metrics) + website_metrics["bytes"],
            "latencies_ms": [item.elapsed_ms for item in metrics] + website_metrics["latencies_ms"],
            "runtime_ms": int((time.monotonic() - company_started) * 1000),
            "third_party_cost_usd": 0,
        }
        profile["run_metrics"] = metric
        return profile, metric

    state: dict[str, dict] = {}
    resumed_profiles = 0
    profiles_output = Path(args.profiles_output)
    if args.resume and profiles_output.exists():
        prior = [json.loads(line) for line in profiles_output.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not set(item["organisation_number"] for item in prior).issubset(set(orgs)):
            raise SystemExit("Resume profile membership is not a subset of this batch")
        state = {
            item["organisation_number"]: item
            for item in prior
            if profile_complete_for_modules(item, requested_modules)
        }
        resumed_profiles = len(state)
    pending_profiles = [profile for profile in profiles if profile["organisation_number"] not in state]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(enrich, profile): profile["organisation_number"] for profile in pending_profiles}
        for index, future in enumerate(as_completed(futures), 1):
            try:
                profile, metric = future.result()
            except Exception as exc:
                org = futures[future]
                profile = next(item for item in profiles if item["organisation_number"] == org)
                for module in requested_modules:
                    profile["evidence"].setdefault(module, evidence(module, "source_error", "batch_worker", "https://data.brreg.no/", note=f"{type(exc).__name__}: {str(exc)[:180]}"))
                profile["worker_error"] = type(exc).__name__
                profile["run_metrics"] = {"requests": None, "runtime_ms": None, "third_party_cost_usd": 0, "note": "Worker failed; partial operations were not fully measured"}
                metric = {"requests": 0, "bytes": 0, "latencies_ms": []}
            state[profile["organisation_number"]] = profile
            operations["requests"] += metric["requests"]
            operations["bytes"] += metric["bytes"]
            operations["latencies_ms"].extend(metric["latencies_ms"])
            if index % args.checkpoint_every == 0 or index == len(pending_profiles):
                checkpoint = [state[org] for org in orgs if org in state]
                write_jsonl(profiles_output, checkpoint)

    completed_at = utc_now()
    ordered_profiles = [state[org] for org in orgs]
    # Resume caches may predate the audit policy. Revalidate before emission.
    for profile in ordered_profiles:
        website_record = profile.get("evidence", {}).get("website")
        if website_record:
            profile["evidence"]["website"] = apply_website_identity_gate(profile, website_record)["website"]
        assess_financial_freshness(profile)
    previous_by_org = {}
    previous_hash = None
    if args.previous_profiles:
        previous_path = Path(args.previous_profiles)
        previous_hash = hashlib.sha256(previous_path.read_bytes()).hexdigest()
        previous_rows = [json.loads(line) for line in previous_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        previous_by_org = {row["organisation_number"]: row for row in previous_rows}
        if len(previous_by_org) != len(previous_rows) or set(previous_by_org) != set(orgs):
            raise SystemExit("Previous snapshot must contain exactly the current organisation membership")
    changes = []
    for profile in ordered_profiles:
        previous = previous_by_org.get(profile["organisation_number"])
        profile["change_history"] = diff_profile(previous, profile) if previous else []
        if previous:
            profile["previous_evidence"] = previous.get("evidence", {})
        source_status_changes = []
        if previous:
            for module in requested_modules:
                old_state = availability(previous.get("evidence", {}).get(module), module)
                new_state = availability(profile.get("evidence", {}).get(module), module)
                if old_state != new_state:
                    source_status_changes.append({"module": module, "old_state": old_state, "new_state": new_state})
        profile["refresh_metadata"] = {"previous_snapshot_sha256": previous_hash, "no_material_changes": not profile["change_history"] if previous else None, "source_status_changes": source_status_changes}
        changes.extend(profile["change_history"])
    write_jsonl(Path(args.changes_output) if args.changes_output else Path(args.output).with_name("changes.jsonl"), changes)
    envelopes = [
        terminal_envelope(profile, run_id=args.run_id, modules=requested_modules, started_at=started_at, completed_at=completed_at)
        for profile in ordered_profiles
    ]
    validation = validate_envelopes(envelopes, args.expected_count)
    write_jsonl(profiles_output, ordered_profiles)
    write_jsonl(Path(args.output), envelopes)
    latencies = sorted(operations.pop("latencies_ms"))
    operations["p50_ms"] = latencies[len(latencies) // 2] if latencies else None
    operations["p95_ms"] = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else None
    report = {
        "run_id": args.run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "expected_count": args.expected_count,
        "emitted_envelopes": len(envelopes),
        "resumed_profiles": resumed_profiles,
        "profiles_fetched_this_run": len(pending_profiles),
        "modules": requested_modules,
        "registry": registry_metadata,
        "operations": operations,
        "runtime_ms": int((time.monotonic() - run_started) * 1000),
        "company_runtime": latency_summary(row.get("run_metrics", {}).get("runtime_ms") for row in ordered_profiles if row.get("run_metrics", {}).get("runtime_ms") is not None),
        "third_party_cost_usd": 0,
        "worker_failures": sum(bool(row.get("worker_error")) for row in ordered_profiles),
        "changes": len(changes),
        "validation": validation,
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if validation["passed"] else 1)


if __name__ == "__main__":
    main()
