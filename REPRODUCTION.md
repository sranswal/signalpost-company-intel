# Revision 2: reproduction and declarations

## Setup and official command

Clone `https://github.com/sranswal/signalpost-company-intel.git`, check out the exact commit in the submission email, and run:

```bash
uv sync --locked
uv run --locked python scripts/run_competition_batch.py --organisations evaluator-companies.jsonl --bulk brreg-enheter.csv --profiles-output out/run/profiles.jsonl --output out/run/envelopes.jsonl --report out/run/report.json --run-id evaluator-run
```

Python 3.12+ is required. The official input and frozen registry snapshot come from Builderr. The runner infers batch size, preserving input order and returning exactly one terminal envelope per input. It does not use the included local smoke manifest unless explicitly asked.

## Smoke and refresh

The checked-in sample contains 100 companies excluded from both prior 1,000-company manifests and the previous live-validation sample. Selection is deterministic and stratified: 70 registry websites, 30 without. It deliberately exercises ownership checks and is not a representative coverage estimate.

Run the same live sample:

```bash
uv run --locked python scripts/run_competition_batch.py --organisations submission/v2/smoke-companies.jsonl --bulk brreg-enheter.csv --profiles-output out/smoke/profiles.jsonl --output out/smoke/envelopes.jsonl --report out/smoke/report.json --run-id local-smoke --previous-profiles submission/v2/previous-profiles.jsonl
```

This makes fresh public requests, so values and hashes can change. The snapshot replay and unit tests are the deterministic checks:

```bash
uv run --locked python -m pytest -q
uv run --locked python scripts/run_refresh_replay.py --manifest tests/fixtures/refresh-snapshots.json --output out/replay.json
```

The source-only `first_run.py` uses saved public responses and makes no network calls.

## Models, APIs and cost

- Production inference: deterministic extraction and rules. No LLM, weights or model API key.
- Official sources: public BRREG entity, roles, group, subunit and accounts APIs; frozen registry CSV supplied by the evaluator.
- Website access: bounded static HTTP(S), public-address checks at redirects, robots checks, byte and timeout limits. Private, reserved, multicast and credential-bearing URL targets are blocked. Robots failures abstain except an absent 404/410 file. DNS is checked before requests; the deployment should additionally enforce egress rules against DNS rebinding.
- Public-suffix parsing uses the library's bundled snapshot and does not download a suffix list during a run.
- No social-platform pages are fetched by the production command. Outbound social links are identity candidates, and only conservative exact matches are published.
- Third-party API cost: $0 per 100-company run and $0 per official run at any batch size. Compute, bandwidth and hosting are separate and environment-dependent.
- External caches: the evaluator's frozen registry CSV, optional explicit previous snapshots and explicit `--resume` checkpoints only. No hidden paid-provider or personal-account cache is required.
- Rights and dependency licences: [SOURCE_RIGHTS.md](SOURCE_RIGHTS.md). Exact dependency versions are in `uv.lock`.

## Evidence and known limits

`claims` is the publication boundary. Candidate websites, rejected social handles and group financial statements remain labelled source data, not claims about the legal entity. Freshness is a reporting-year check against the live registry, not proof that an API has exposed every amendment. A stale response is flagged, never presented as a verified current filing. The open accounts API can omit specialist accounting layouts and can be unavailable.

The matching rules are intentionally conservative. Legitimate brand names and social aliases can be missed. Independent sentiment, audience/traffic metrics, platform metrics and licensed external news are unavailable in the production command. Source markup is untrusted; only specific original-publication fields on news paths are accepted.

An operational smoke pass is not a measured real-world precision or recall score. Only Builderr's official run establishes competition qualification. See `submission/v2` for actual measured results, not historical starter claims or hashes.
