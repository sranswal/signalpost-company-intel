# Audit hardening: revision 2 (30 October 2026)

## Audit feedback and fixes

1. Company ownership: contiguous legal-name evidence and bounded organisation-number matches; group sites, conflicting identities, domain-only titles and cookie-only placeholders abstain. Legal-name segments in page titles are supported without requiring the name to appear first.
2. Social ownership: an accepted company site plus a full normalized legal-name handle match. Agency/theme attribution links and partial/parent handles are excluded. Legitimate aliases can be missed; this is not independent verification of platform ownership.
3. News: require a dated individual news path, article metadata, original publication date and content hash. Homepage, about, product and archive metadata are not news. Modified/updated dates are never substituted for publication dates.
4. Latest accounts: the live BRREG sample returned three group records followed by three company records. The original cutoff could discard all company records. Records now sort before selection, company and group scopes are separated, freshness checks the live registry year, and compatible comparisons run older to newer.

## Operational hardening

- Six public states, explicit claims and resolvable evidence references; rejected candidates are labelled source snapshots.
- Variable-size evaluator batches and one terminal result per input, including worker failures.
- Live registry identity fields supersede stale bulk fields; the reader accepts both plain and gzip CSV.
- Explicit previous snapshots, preserved prior evidence, material changes and source-availability changes. Blocked/error rechecks never claim that a business fact disappeared.
- Atomic checkpoints and revalidation of cached ownership gates.
- Locked production/test dependencies; offline public-suffix snapshot; bounded public-only crawling and conservative robots failures.
- Pytest collects the working tests rather than an old staging duplicate.

## Validation artifacts

`submission/v2` contains the unseen 100-company manifest, live source snapshots, terminal envelopes, run report, source-evidence review, schema/provenance validation, refresh replay and regenerated showcase. The sample is deliberately stratified to exercise website ownership checks, not to estimate population coverage.

The regression suite passes 131 tests and 5 subtests. A fresh Python 3.12 environment installs with `uv sync --locked`. Final clean-checkout evidence is saved alongside the release package. Test success is not an official competition score or an independently measured zero-error rate.

Old production-1000 artifacts and old staging archives belong to version 1. Revision 2 is based on the current [evaluation contract](https://builderr.ai/docs/signalpost-evaluation-harness.md): fresh evaluator batches plus a 100-company operational smoke report.
