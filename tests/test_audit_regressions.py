from bs4 import BeautifulSoup
from norway_company_agent.identity import assess_website_identity, assess_social_identity
from norway_company_agent.news import article_metadata
from norway_company_agent.official import normalize_financials, comparable_financials, assess_financial_freshness


def test_parent_directory_cannot_claim_subsidiary_website():
    profile = {"name": "Fjord Seafood AS", "organisation_number": "923609016", "evidence": {"website": {"value": {
        "title": "Parent Holding AS", "main_text_excerpt": "Our subsidiary Fjord Seafood AS, 923609016. Parent Holding AS 987654321.",
    }}}}
    assert not assess_website_identity(profile)["publishable"]
    profile["evidence"]["website"]["value"]["main_text_excerpt"] = "Our subsidiary Fjord Seafood AS, 923609016."
    assert not assess_website_identity(profile)["publishable"]


def test_handle_substrings_and_parent_extensions_are_not_exact():
    for name, handle in [("Aon AS", "aonagency"), ("Fjord Seafood AS", "fjord-seafood-group"), ("Fjord Seafood AS", "fjord-seafood-webdesign")]:
        assert not assess_social_identity({"name": name}, {"url": "https://linkedin.com/company/" + handle})["publishable"]


def test_article_requires_original_publish_date_and_matching_url():
    def extract(payload):
        import json
        soup = BeautifulSoup('<article><h1>Contract</h1></article><script type="application/ld+json">' + json.dumps(payload) + '</script>', "lxml")
        return article_metadata(soup, "https://example.no/news/contract")
    base = {"@type": "NewsArticle", "headline": "Contract", "url": "https://example.no/news/contract"}
    assert not extract({**base, "dateModified": "2025-01-01"})
    assert not extract({**base, "datePublished": "2099-01-01"})
    assert not extract({**base, "datePublished": "2025-01-01", "url": "https://example.no/product"})
    assert extract({**base, "datePublished": "2025-01-01"})["publication_date_source"] == "jsonld.datePublished"


def test_latest_financial_is_sorted_before_limiting():
    rows = [{"id": str(year), "regnskapsperiode": {"fraDato": f"{year}-01-01", "tilDato": f"{year}-12-31"}, "valuta": "NOK", "regnskapstype": "SELSKAP"} for year in [2022, 2023, 2024, 2025]]
    value = normalize_financials(rows)
    assert value["records"][0]["record_id"] == "2025"
    assert [item["record_id"] for item in value["comparison"]] == ["2024", "2025"]
    profile = {"latest_submitted_accounts": "2025", "evidence": {"financials": {"status": "available", "value": {"records": value["records"][1:]}}}}
    assess_financial_freshness(profile)
    assert not profile["evidence"]["financials"]["value"]["freshness"]["latest_verified"]


def test_incompatible_periods_and_currency_abstain():
    newer = {"period": {"fraDato": "2025-01-01", "tilDato": "2025-12-31"}, "currency": "NOK", "account_type": "SELSKAP"}
    older = {**newer, "period": {"fraDato": "2024-07-01", "tilDato": "2024-12-31"}}
    assert comparable_financials([newer, older]) == []
    older.update(period={"fraDato": "2024-01-01", "tilDato": "2024-12-31"}, currency="EUR")
    assert comparable_financials([newer, older]) == []


def test_undated_navigation_is_not_news():
    from scripts.extract_company_site_news import observation
    profile = {"organisation_number": "923609016", "evidence": {"website": {"status": "available", "value": {"identity_assessment": {"publishable": True}, "pages": [{"url": "https://example.no/news", "title": "See more news", "content_sha256": "a" * 64, "updated": "2025-01-01"}]}}}}
    assert observation(profile) is None


def test_dated_homepage_and_product_metadata_are_not_news():
    from norway_company_agent.news import is_news_page
    base = {"article_title": "Our services", "article_type": "article", "publication_date_source": "article:published_time", "published_at": "2025-01-01", "content_sha256": "a" * 64}
    for path in ("/", "/products/service", "/about-us", "/news/"):
        assert not is_news_page({**base, "url": "https://example.no" + path})
    assert is_news_page({**base, "url": "https://example.no/news/contract"})


def test_domain_title_and_cookie_banner_are_not_website_identity():
    row = {"organisation_number": "983906818", "name": "KBTE AS", "evidence": {"website": {"value": {"final_url": "https://kbte.no/", "title": "kbte.no", "main_text_excerpt": "Vi bruker informasjonskapsler " * 20}}}}
    assert not assess_website_identity(row)["publishable"]


def test_blocked_refresh_does_not_claim_business_fact_disappeared():
    from norway_company_agent.refresh import diff_profile
    old = {"organisation_number": "923609016", "evidence": {"website": {"status": "available", "value": {"title": "Example", "identity_assessment": {"publishable": True}}}}}
    new = {"organisation_number": "923609016", "evidence": {"website": {"status": "blocked", "value": None}}}
    assert diff_profile(old, new) == []


def test_group_accounts_cannot_replace_entity_accounts():
    period = {"fraDato": "2025-01-01", "tilDato": "2025-12-31"}
    value = normalize_financials([{"id": 99, "regnskapstype": "KONSERN", "regnskapsperiode": period}, {"id": 1, "regnskapstype": "SELSKAP", "regnskapsperiode": period}])
    assert [row["account_type"] for row in value["records"]] == ["SELSKAP"]
    assert [row["account_type"] for row in value["group_records"]] == ["KONSERN"]
    assert normalize_financials([{"regnskapstype": "KONSERN", "regnskapsperiode": period}])["records"] == []


def test_public_envelope_quarantines_unverified_site_and_has_resolvable_evidence():
    from norway_company_agent.batch import terminal_envelope, validate_envelopes
    from norway_company_agent.evidence import evidence
    profile = {"organisation_number": "923609016", "name": "Subsidiary AS", "evidence": {"website": evidence("website", "available", "company_site", "https://parent.no", value={"description": "Parent business", "social_links": [{"url": "https://facebook.com/parent"}], "identity_assessment": {"publishable": False}})}}
    row = terminal_envelope(profile, run_id="test", modules=["website"], started_at="2026-01-01", completed_at="2026-01-01")
    assert row["state"] == "ambiguous"
    assert row["claims"][0]["value"] is None
    assert not any(claim["field"] == "social_account" for claim in row["claims"])
    assert all(ref in {source["id"] for source in row["evidence"]} for claim in row["claims"] for ref in claim["evidence_ids"])
    assert validate_envelopes([row], 1)["passed"]


def test_batch_worker_failure_emits_exactly_one_row_per_input(tmp_path, monkeypatch):
    import json
    import sys
    from scripts import run_competition_batch as runner
    manifest, bulk = tmp_path / "input.jsonl", tmp_path / "bulk.csv"
    manifest.write_text('\n'.join(json.dumps({"organisation_number": str(org)}) for org in (923609016, 985628572)), encoding="utf-8")
    bulk.write_text("organisasjonsnummer;navn;organisasjonsform.kode\n923609016;A AS;AS\n985628572;B AS;AS\n", encoding="utf-8")
    def fetch(org, modules):
        if org == "985628572":
            raise RuntimeError("simulated worker failure")
        return {}, []
    monkeypatch.setattr(runner, "fetch_official_modules", fetch)
    monkeypatch.setattr(sys, "argv", ["runner", "--organisations", str(manifest), "--bulk", str(bulk), "--profiles-output", str(tmp_path / "profiles.jsonl"), "--output", str(tmp_path / "envelopes.jsonl"), "--report", str(tmp_path / "report.json"), "--run-id", "test", "--modules", "registry"])
    import pytest
    with pytest.raises(SystemExit) as exit_info:
        runner.main()
    assert exit_info.value.code == 0
    rows = [json.loads(line) for line in (tmp_path / "envelopes.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["organisation_number"] for row in rows] == ["923609016", "985628572"]
    assert rows[1]["state"] == "failed"
    assert json.loads((tmp_path / "report.json").read_text())["worker_failures"] == 1
