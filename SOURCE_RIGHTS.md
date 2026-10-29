# Production source rights and dependencies

The production command uses public BRREG data and ordinary bounded requests to company websites. It does not execute the experimental LinkedIn, Google News, reviews, video or search connector scripts.

## Official registry data

BRREG public open data is attributed to Bronnoysundregistrene and used under the published [Norwegian Licence for Open Government Data, NLOD 2.0](https://data.norge.no/nlod/en/2.0). See the [official accounts service catalogue](https://data.norge.no/en/data-services/4dabc5ea-b57b-3b68-9e48-2ff993be3f6e/nokkeltall-fra-arsregnskapet) and [BRREG API documentation](https://data.brreg.no/regnskapsregisteret/regnskap/swagger-ui/index.html).

Frozen registry files are evaluator inputs, not bundled upstream datasets. Live official responses retain their source URLs, retrieval times and hashes. Group statements and legal-entity statements are kept distinct. Public roles can include personal names; no personal identity numbers are requested or inferred.

## Company websites

Company content remains subject to the website owner's rights and terms. This submission assumes ordinary public retrieval of bounded pages for factual extraction is permitted where robots and site terms allow it. Robots compliance alone is not a universal licence. The crawler blocks explicit disallows and failed robots checks, respects byte/time bounds, and does not bypass logins, paywalls or anti-bot challenges. Captured excerpts are evidence, not a republication of complete articles. Hosts can be excluded by the evaluator's network policy.

Social links are extracted from accepted company pages; no LinkedIn, Meta, TikTok or YouTube scraping occurs in production. No platform audience counts or independent sentiment are inferred from those links.

## Software

Exact production and test dependency versions and distribution hashes are in `uv.lock`. The generated `submission/v2/dependency-inventory.json` records the installed distributions and their licence metadata. Dependency licences remain with their respective authors; this document does not relicense them. The repository does not currently declare a separate code licence.

No secrets, personal provider credentials, paid search caches, LLM tokens or proprietary inference models are required. External API charges are $0; local compute and bandwidth are not included in that figure.

The challenge's [source policy](https://builderr.ai/starter-briefs/signalpost-sources.md) and [evaluation contract](https://builderr.ai/docs/signalpost-evaluation-harness.md) govern submission use.
