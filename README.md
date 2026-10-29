# Signalpost company intelligence agent

A deterministic Norwegian company-research agent for the [Signalpost challenge](https://builderr.ai/challenges/signalpost). It accepts evaluator-supplied organisation numbers, anchors identity in BRREG, and returns one source-linked terminal result per company.

## Reproduce

Requires Python 3.12+ and uv. Install the exact dependency lock:

```bash
uv sync --locked
```

Builderr supplies the frozen registry snapshot and official input batch. For local work, download the public registry snapshot:

```bash
curl -L https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv -o brreg-enheter.csv
```

Run any evaluator batch, without changing code or choosing replacement companies:

```bash
uv run --locked python scripts/run_competition_batch.py --organisations evaluator-companies.jsonl --bulk brreg-enheter.csv --profiles-output out/run/profiles.jsonl --output out/run/envelopes.jsonl --report out/run/report.json --run-id evaluator-run
```

The input length is inferred. An optional `--expected-count` asserts a specific count. JSONL rows contain `organisation_number`; JSON arrays and one-number-per-line files are also accepted. Both plain and gzip-compressed registry CSV files work.

## What is published

- Official legal identity, roles, locations, group relationships and company-level annual accounts.
- A company website only after exact-entity evidence passes. Group, brand, property-manager and uncertain pages remain candidate evidence.
- Social accounts only from an accepted site and an exact full normalized handle match. This conservative heuristic can miss legitimate aliases.
- News only from dated individual news/article paths with original publication metadata. Homepage, product, about, archive and modified-only dates are excluded.
- Accounts sorted by reporting period before selection, with group statements kept separately. Freshness is checked against the live registry year; comparisons use compatible periods, currencies and account scopes, older to newer.

Public facts are in `claims`. Raw source candidates in `profile` and `evidence` are labelled and must not be treated as published facts. Every claim references evidence with a source URL, retrieval timestamp and hash where a response was captured. The six public states are `available`, `not_available`, `blocked`, `not_applicable`, `ambiguous` and `failed`.

## Refresh and resilience

Append `--previous-profiles out/previous/profiles.jsonl` to preserve the prior evidence and emit `changes.jsonl` beside the envelopes. Previous snapshots must contain the same company membership. Retrieval timestamps alone do not create changes. `--changes-output` overrides the change-file path.

Each company gets a terminal row even if a worker fails. Checkpoint files are written atomically. `--resume` revalidates cached identity gates but does not make cached evidence fresh; use a fresh run for official evaluation.

## Validation and review

```bash
uv run --locked python -m pytest -q
uv run --locked python first_run.py
```

The pinned development dependency is included by `uv sync --locked`. In restricted Windows environments, use `--basetemp .tmp-pytest` if the shared temporary directory is inaccessible.

The [revision-2 smoke artifacts](submission/v2/README.md) document an unseen 100-company sample, live runs, evidence review and replay checks. They are operational diagnostics, not an official competition score. Older `out/production-1000` artifacts belong to version 1 and are not revision-2 evidence.

See [reproduction and declarations](REPRODUCTION.md), [output schema](OUTPUT_CONTRACT.md), [source rights](SOURCE_RIGHTS.md), and [audit changes](docs/audit-hardening.md).

No LLM, paid search provider or platform scraper is used by the documented production command. Third-party API charges are $0; hosting and network costs depend on the evaluator environment. Experimental connector scripts are excluded from the production command.
