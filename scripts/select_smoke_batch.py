"""Freeze a reproducible unseen sample; never substitute it for evaluator inputs."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import heapq
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", required=True)
    parser.add_argument("--exclude", nargs="*", default=[])
    parser.add_argument("--output", required=True)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", default="signalpost-audit-v2-20261030")
    args = parser.parse_args()
    excluded = set()
    for name in args.exclude:
        for line in Path(name).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                excluded.add(str(row["organisation_number"]))
    opener = gzip.open if args.universe.endswith(".gz") else open
    with opener(args.universe, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    eligible = [row for row in rows if str(row["organisation_number"]) not in excluded]
    def rank(row):
        return hashlib.sha256(f"{args.seed}|{row['organisation_number']}".encode()).hexdigest()
    # Exercise website gates deliberately; keep a no-website stratum as well.
    web_count = args.count * 7 // 10
    selected = heapq.nsmallest(web_count, (row for row in eligible if row.get("website")), key=rank)
    selected += heapq.nsmallest(args.count - web_count, (row for row in eligible if not row.get("website")), key=rank)
    selected.sort(key=rank)
    if len(selected) != args.count:
        raise SystemExit("Not enough unseen companies in each stratum")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps({"organisation_number": row["organisation_number"], "evaluation_split": "fresh_local_smoke", "sample_slice": "website" if row.get("website") else "no_registry_website"}) + "\n" for row in selected), encoding="utf-8")
    metadata = {"seed": args.seed, "count": len(selected), "with_registry_website": web_count, "excluded": len(excluded), "overlap_with_excluded": len({row['organisation_number'] for row in selected} & excluded), "universe_sha256": hashlib.sha256(Path(args.universe).read_bytes()).hexdigest(), "manifest_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "purpose": "Stratified operational smoke; not an unbiased coverage estimate or official score"}
    output.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
