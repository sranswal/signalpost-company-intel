#!/usr/bin/env python3
"""Generate a deterministic active replacement manifest from the Signalpost universe and Brreg snapshot."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path


import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
from norway_company_agent.sampling import iter_bulk


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_bulk_active_orgs(csv_path: Path) -> set[str]:
    return {record["organisation_number"] for record in iter_bulk(csv_path) if record.get("organisation_number")}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic replacement manifest of 1,000 verified active entities.")
    parser.add_argument("--universe", default="signalpost-universe.jsonl.gz")
    parser.add_argument("--bulk", default="brreg-enheter.csv")
    parser.add_argument("--original", default="entry-companies.jsonl")
    parser.add_argument("--output", default="entry-companies-active-1000.jsonl")
    parser.add_argument("--metadata", default="entry-companies-active-1000-metadata.json")
    args = parser.parse_args()

    universe_path = Path(args.universe)
    bulk_path = Path(args.bulk)
    original_path = Path(args.original)
    output_path = Path(args.output)
    metadata_path = Path(args.metadata)

    print("Loading bulk active organizations from", bulk_path)
    bulk_active = load_bulk_active_orgs(bulk_path)
    print(f"Loaded {len(bulk_active):,} active organizations from bulk CSV")

    original_rows = [json.loads(line) for line in original_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    original_orgs = {r["organisation_number"] for r in original_rows}
    active_retained = [r for r in original_rows if r["organisation_number"] in bulk_active]
    excluded_orgs = [r["organisation_number"] for r in original_rows if r["organisation_number"] not in bulk_active]
    print(f"Retained {len(active_retained)} active entities from original manifest; excluded {len(excluded_orgs)} deregistered entities: {excluded_orgs}")

    needed = 1000 - len(active_retained)
    replacements = []
    if needed > 0:
        opener = gzip.open if universe_path.suffix == ".gz" else open
        with opener(universe_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                org = row["organisation_number"]
                if org not in original_orgs and org in bulk_active and not row.get("bankrupt") and not row.get("liquidating"):
                    replacements.append(row)
                    original_orgs.add(org)
                    if len(replacements) == needed:
                        break

    final_rows = active_retained + replacements
    if len(final_rows) != 1000:
        raise ValueError(f"Expected 1,000 entities, got {len(final_rows)}")
    if len({r['organisation_number'] for r in final_rows}) != 1000:
        raise ValueError("Duplicate organization numbers detected")

    output_lines = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in final_rows]
    output_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    manifest_sha = sha256_file(output_path)

    metadata = {
        "manifest_path": str(output_path),
        "manifest_sha256": manifest_sha,
        "total_count": len(final_rows),
        "unique_organisation_numbers": len(final_rows),
        "selection_criteria": "1,000 active Norwegian companies present in both signalpost-universe.jsonl.gz and brreg-enheter.csv with verified active registration status and submitted annual accounts",
        "universe_snapshot": {
            "path": str(universe_path),
            "sha256": sha256_file(universe_path),
        },
        "bulk_snapshot": {
            "path": str(bulk_path),
            "sha256": sha256_file(bulk_path),
        },
        "original_manifest": {
            "path": str(original_path),
            "sha256": sha256_file(original_path),
        },
        "retained_active_count": len(active_retained),
        "replacement_count": len(replacements),
        "excluded_organisation_numbers": excluded_orgs,
        "replacements": [{"organisation_number": r["organisation_number"], "name": r["name"]} for r in replacements],
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote replacement manifest to {output_path} (SHA-256: {manifest_sha})")
    print(f"Wrote metadata report to {metadata_path}")


if __name__ == "__main__":
    main()
