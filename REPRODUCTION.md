# SignalPost: Submission Reproduction Guide & Declarations

This document provides exact reproduction instructions, operational declarations, and artifact verification hashes for the SignalPost competition submission.

---

## 1. System Requirements & Environment

- **Python**: 3.12 or newer.
- **Package Manager**: `uv` (Astral).
- **Supported Platforms**: Windows (PowerShell), Linux, macOS.

### Installation
From the root of this repository:
```bash
uv sync --locked
```

---

## 2. Starter & Contract Replay Verification

Run the previous-snapshot and material-change replay verification:
```bash
uv run --locked python first_run.py
```
**Expected Output**:
```
Signalpost starter: SUCCESS
It found both saved changes, added no false change, kept the evidence, and produced the same result on a repeat check.
Result: .../out/refresh-demo.json
```

---

## 3. Automated Test Suite

Run the full unit and integration test suite:
```bash
uv run --with pytest pytest -q
```
**Expected Result**:
```
119 passed, 5 subtests passed in ~5-7s (0 failures)
```

---

## 4. Production 1,000-Company Batch Execution

### Input Requirements
1. **Manifest**: `entry-companies.jsonl` (bundled in the repository root, containing exactly 1,000 unique Norwegian organisation numbers).
2. **Bulk Snapshot**: `brreg-enheter.csv` (official public snapshot from Brønnøysundregistrene).

#### Obtaining `brreg-enheter.csv` Legally
- **Licence & Open Data Authority**:
  The Enhetsregisteret bulk dataset is published by Brønnøysundregistrene under the **Norwegian Licence for Open Government Data (NLOD 2.0)** / **Creative Commons Attribution 4.0 International (CC BY 4.0)**. Free for commercial, non-commercial, and evaluation purposes.
- **Why it is not bundled**:
  In accordance with competition rules and repository hygiene, bulky upstream register dumps (~148 MB) are not committed to Git or bundled in distribution archives.
- **Download Instructions**:
  - *Linux / macOS / Git Bash*:
    ```bash
    curl -L "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv" -o brreg-enheter.csv
    ```
  - *Windows PowerShell*:
    ```powershell
    curl.exe -L "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv" -o brreg-enheter.csv
    ```
    or
    ```powershell
    Invoke-WebRequest -Uri "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv" -OutFile "brreg-enheter.csv"
    ```
- **Format Compatibility**:
  Brønnøysundregistrene serves the bulk endpoint as a gzip-compressed CSV stream. SignalPost's built-in `iter_bulk` automatically detects compression magic bytes (`1f 8b`) and sniffs the CSV delimiter (comma `,` or semicolon `;`). It accepts either compressed or uncompressed snapshots seamlessly. If you already have an existing local snapshot, simply point `--bulk <path>` to it.

### Execution Command
```bash
uv run python scripts/run_competition_batch.py \
  --organisations entry-companies.jsonl \
  --bulk brreg-enheter.csv \
  --profiles-output out/production-1000/profiles.jsonl \
  --output out/production-1000/envelopes.jsonl \
  --report out/production-1000/report.json \
  --run-id run-production-1000-001 \
  --expected-count 1000 \
  --workers 8 \
  --checkpoint-every 25 \
  --resume
```

### Expected Outputs
- `out/production-1000/envelopes.jsonl`: Exactly 1,000 terminal envelopes in identical order as `entry-companies.jsonl`, all in valid terminal states (`complete`). Zero silent drops.
- `out/production-1000/profiles.jsonl`: Exactly 1,000 enriched company profiles with full evidence provenance and content hashes.
- `out/production-1000/report.json`: Machine-readable operational report documenting runtime, requests, bytes transferred, p50/p95 latency, and envelope validation results.

---

## 5. Declarations of Models, APIs, Licences & Source Rights

1. **APIs & Data Sources**:
   - **Brønnøysundregistrene Enhetsregisteret & Regnskapsregisteret**: Official Norwegian public register data fetched via `data.brreg.no`.
   - **Licence**: Norwegian Licence for Open Government Data (NLOD 2.0).
   - **Cost**: **$0.00** (Free, open public access).
2. **Website Crawling & Identity Gating**:
   - **Acquisition Mode**: Polite static HTTP/HTTPS crawling with bounded page depth, standard request headers, timeout guards, and strict adherence to `robots.txt`.
   - **Identity Proof**: Two-token exact entity match against legal name tokens. Unverified parent/franchise/brand domains are quarantined (`publishable: false`).
   - **Wrong-Entity Publications**: **0**.
3. **Model / Inference Declarations**:
   - **Inference**: Fully deterministic rule-based extractors, regex parsers, and SHA-256 evidence digests. No paid commercial LLM tokens or external inference endpoints were invoked.
   - **Expected Cost per 100-company run**: **$0.00**.
4. **Quarantined Connectors**:
   - Google News RSS and external customer review scrapers were evaluated but kept strictly **quarantined** and excluded from production due to licensing restrictions, TOS boundaries, and risk of unverified entity matching.

---

## 6. Official Submission Hashes

| Artifact Path | SHA-256 Digest |
| :--- | :--- |
| `entry-companies.jsonl` | `b1ea2f59791e1a73300ba46d3f7322614446040f18939758c162ba07633b2cb0` |
| `out/production-1000/envelopes.jsonl` | `8d92d0724271bf415f3a801334307ee87ed7c3aa1390124ca9f19a910ec507f7` |
| `out/production-1000/profiles.jsonl` | `f91ac75896bd326365ff4390a5803e7db012a042482da5b11cadc9977b6ce070` |
| `out/production-1000/report.json` | `8dfad63b5b9cafa659b939fa984f0d7feab263d179a4b5678f22db47f8b62ca9` |
| `out/production-1000/activity.jsonl` | `fc5a18a186952e343f70cc6f8ed57cd5209b53d8c5b90e469b1a118cda75701a` |
| `out/production-1000/activity-report.json` | `74e66ab238805385e003543e11d0ca1cdd17f9078b74dbadc45e1e4294ee55da` |
| `out/production-1000/score-report.json` | `33cc9a5fbcebe16ea8efcbeb4d8c5058000180ba752ce6bf13dbcc2c19410947` |
