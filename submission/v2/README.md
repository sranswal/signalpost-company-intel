# Revision 2 smoke and review artifacts

This is a local operational sample, not Builderr's official evaluation score. Builderr supplies the actual company batch at run time.

## Measured final run

- Date: 30 October 2026, Asia/Kolkata (raw timestamps are UTC).
- Inputs/results: 100/100, original order preserved; no missing or duplicate results.
- Runtime: 180.922 seconds with 8 workers.
- Application request attempts: 817; wire redirects can add requests.
- Company latency: p50 7.296s, p95 26.781s.
- Worker failures: 0. Third-party API charges: $0; compute and bandwidth excluded.
- Latest company-account reporting years: 99 FY2025 and 1 FY2026; all match the live registry year.
- Published websites: 18; published social links: 9; ambiguous available websites withheld: 33.
- Eligible dated news posts: 0. No homepage/product/archive content is counted as news.
- Material changes against the first live snapshots: 0. Source-availability changes are recorded separately.
- Regression suite: 131 tests and 5 subtests pass. Snapshot fixture: both expected changes found, no false changes, identical rerun adds nothing.

## Files

- `smoke-companies.jsonl`, `.metadata.json`: deterministic unseen input and selection provenance; zero overlap with prior manifests.
- `smoke-report.json`: actual final live-run measurements.
- `profiles.jsonl`, `envelopes.jsonl`: live evidence and six-state public results. Candidate snapshots are not published claims.
- `previous-profiles.jsonl`, `baseline-report.json`, `changes.jsonl`: first live evidence, baseline operational report and final material differences.
- `validation-report.json`: order/membership, public evidence references, ownership boundaries and account-scope checks.
- `evidence-review.json`: Codex review notes for every published website/social link and quarantined site candidates; not independent human ground truth.
- `refresh-replay.json`: deterministic old/new fixture replay, separate from competition qualification.
- `showcase.html`: regenerated self-contained 100-company evidence browser. Serve it with `python -m http.server` or open it locally.
- `activity*`, `news*`: bounded site-activity extraction and strict-news abstentions.
- `dependency-inventory.json`: locked installed software and licence metadata.

Run `uv sync --locked`, then use the command in the root `REPRODUCTION.md`. The source-only clean-checkout install, tests, CLI and replay were verified separately. Full source/commit and release archive hashes are in the release manifest supplied with the submission email.
