import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from jobsearch.utils import (
    google_search,
    is_allowed_location,
    move_company_to_bad,
    parse_ashby,
    parse_greenhouse,
    parse_lever,
)

GREENHOUSE_URL = "https://boards.greenhouse.io/acme/jobs/123456"
LEVER_URL = "https://jobs.lever.co/acme/abc-123"
ASHBY_URL = "https://jobs.ashbyhq.com/acme/abc-123"
GOOGLE_URL = "https://www.googleapis.com/customsearch/v1"

GREENHOUSE_HTML = """
<html><body>
  <div class="job__title"><h1>Data Engineer</h1></div>
  <div class="job__location">New York, NY</div>
  <div class="job__description">Build data pipelines.</div>
</body></html>
"""

GREENHOUSE_BARE_HTML = "<html><body><p>Nothing here</p></body></html>"

LEVER_LD_JSON = {
    "@context": "http://schema.org",
    "@type": "JobPosting",
    "title": "Data Engineer",
    "jobLocation": {"address": {"addressLocality": "San Francisco"}},
    "description": "<p>Build pipelines</p>",
    "datePosted": "2024-01-15",
}

LEVER_MULTI_LOC_LD_JSON = {
    "@context": "http://schema.org",
    "@type": "JobPosting",
    "title": "Data Engineer",
    "jobLocation": [
        {"address": {"addressLocality": "San Francisco"}},
        {"address": {"addressLocality": "New York"}},
    ],
    "description": "<p>Build pipelines</p>",
    "datePosted": "2024-01-15",
}

LEVER_HTML_TEMPLATE = """
<html><body>
  <script type="application/ld+json">{ld_json}</script>
</body></html>
"""

LEVER_NO_SCRIPT_HTML = "<html><body><p>No script here</p></body></html>"


# ---------------------------------------------------------------------------
# parse_greenhouse
# ---------------------------------------------------------------------------


def test_parse_greenhouse_happy_path(httpx_mock):
    httpx_mock.add_response(url=GREENHOUSE_URL, text=GREENHOUSE_HTML)
    company, title, location, description, date_posted = parse_greenhouse(GREENHOUSE_URL)
    assert company == "acme"
    assert title == "Data Engineer"
    assert location == "New York, NY"
    assert "pipelines" in description
    assert date_posted is None


def test_parse_greenhouse_missing_element(httpx_mock):
    httpx_mock.add_response(url=GREENHOUSE_URL, text=GREENHOUSE_BARE_HTML)
    with pytest.raises(ValueError, match="missing .job__title"):
        parse_greenhouse(GREENHOUSE_URL)


def test_parse_greenhouse_http_404(httpx_mock):
    httpx_mock.add_response(url=GREENHOUSE_URL, status_code=404)
    with pytest.raises(httpx.HTTPStatusError):
        parse_greenhouse(GREENHOUSE_URL)


# ---------------------------------------------------------------------------
# parse_lever
# ---------------------------------------------------------------------------


def test_parse_lever_single_location(httpx_mock):
    html = LEVER_HTML_TEMPLATE.format(ld_json=json.dumps(LEVER_LD_JSON))
    httpx_mock.add_response(url=LEVER_URL, text=html)
    company, title, location, description, date_posted = parse_lever(LEVER_URL)
    assert company == "acme"
    assert title == "Data Engineer"
    assert location == "San Francisco"
    assert date_posted == "2024-01-15"


def test_parse_lever_multi_location(httpx_mock):
    html = LEVER_HTML_TEMPLATE.format(ld_json=json.dumps(LEVER_MULTI_LOC_LD_JSON))
    httpx_mock.add_response(url=LEVER_URL, text=html)
    _, _, location, _, _ = parse_lever(LEVER_URL)
    assert location == "San Francisco/New York"


def test_parse_lever_no_script_tag(httpx_mock):
    httpx_mock.add_response(url=LEVER_URL, text=LEVER_NO_SCRIPT_HTML)
    with pytest.raises(ValueError, match="no application/ld\\+json"):
        parse_lever(LEVER_URL)


# ---------------------------------------------------------------------------
# parse_ashby
# ---------------------------------------------------------------------------


def _ashby_mock(execute_return):
    mock_client = MagicMock()
    mock_client.execute.return_value = execute_return
    return mock_client


def test_parse_ashby_happy_path():
    result = {
        "jobPosting": {
            "title": "Data Engineer",
            "locationName": "Remote",
            "descriptionHtml": "<p>Description</p>",
            "linkedData": {"datePosted": "2024-01-15"},
        }
    }
    with patch("jobsearch.utils.Client", return_value=_ashby_mock(result)):
        company, title, location, description, date_posted = parse_ashby(ASHBY_URL)
    assert company == "acme"
    assert title == "Data Engineer"
    assert location == "Remote"
    assert date_posted == "2024-01-15"


def test_parse_ashby_null_job_posting():
    with patch("jobsearch.utils.Client", return_value=_ashby_mock({"jobPosting": None})):
        with pytest.raises(ValueError, match="jobPosting is null"):
            parse_ashby(ASHBY_URL)


def test_parse_ashby_missing_linked_data():
    result = {
        "jobPosting": {
            "title": "Data Engineer",
            "locationName": "Remote",
            "descriptionHtml": "<p>Description</p>",
            "linkedData": None,
        }
    }
    with patch("jobsearch.utils.Client", return_value=_ashby_mock(result)):
        _, _, _, _, date_posted = parse_ashby(ASHBY_URL)
    assert date_posted is None


# ---------------------------------------------------------------------------
# google_search
# ---------------------------------------------------------------------------


def test_google_search_happy_path(httpx_mock, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CX", "test-cx")
    httpx_mock.add_response(
        json={
            "items": [{"link": "http://example.com", "title": "Test Job", "snippet": "A job"}],
            "queries": {"nextPage": [{"startIndex": 11}]},
        }
    )
    results, queries = google_search("data engineer")
    assert len(results) == 1
    assert results[0]["link"] == "http://example.com"
    assert queries["nextPage"][0]["startIndex"] == 11


def test_google_search_missing_env(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CX", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        google_search("test query")


def test_google_search_retries_on_429(httpx_mock, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CX", "test-cx")
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(json={"items": [], "queries": {}})
    with patch("time.sleep"):
        results, _ = google_search("test")
    assert results == []


def test_google_search_raises_after_max_retries(httpx_mock, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CX", "test-cx")
    for _ in range(4):  # _MAX_RETRIES + 1 attempts
        httpx_mock.add_response(status_code=429)
    with patch("time.sleep"):
        with pytest.raises(httpx.HTTPStatusError):
            google_search("test")


# ---------------------------------------------------------------------------
# move_company_to_bad
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# is_allowed_location
# ---------------------------------------------------------------------------


def test_allowed_location_remote():
    assert is_allowed_location("Remote") is True


def test_allowed_location_remote_us():
    assert is_allowed_location("Remote (US Only)") is True


def test_allowed_location_city_state():
    assert is_allowed_location("New York, NY") is True


def test_allowed_location_bare_city():
    assert is_allowed_location("New York") is True


def test_allowed_location_empty():
    assert is_allowed_location("") is True


def test_blocked_location_india():
    assert is_allowed_location("India") is False


def test_blocked_location_city_country():
    assert is_allowed_location("Bangalore, India") is False


def test_blocked_location_uk_city():
    assert is_allowed_location("London") is False


def test_blocked_location_london_uk():
    assert is_allowed_location("London, UK") is False


def test_blocked_location_emea():
    assert is_allowed_location("Remote - EMEA") is False


def test_blocked_location_germany():
    assert is_allowed_location("Berlin, Germany") is False


def test_blocked_location_canada():
    assert is_allowed_location("Toronto") is False


def test_extra_blocked_matches():
    assert is_allowed_location("Warsaw", extra_blocked=frozenset({"Warsaw"})) is False


def test_extra_blocked_no_match():
    assert is_allowed_location("New York", extra_blocked=frozenset({"Warsaw"})) is True


def test_extra_blocked_case_insensitive():
    assert is_allowed_location("warsaw", extra_blocked=frozenset({"Warsaw"})) is False


@pytest.mark.django_db
def test_move_company_to_bad_moves_records():
    from jobsearch.models import BadJob, JobPosting

    JobPosting.objects.create(url="https://jobs.lever.co/acme/1", company="acme", title="DE 1")
    JobPosting.objects.create(url="https://jobs.lever.co/acme/2", company="acme", title="DE 2")

    move_company_to_bad("acme")

    assert JobPosting.objects.filter(company="acme").count() == 0
    assert BadJob.objects.filter(company="acme").count() == 2


@pytest.mark.django_db
def test_move_company_to_bad_idempotent():
    from jobsearch.models import BadJob, JobPosting

    JobPosting.objects.create(url="https://jobs.lever.co/acme/1", company="acme", title="DE 1")

    move_company_to_bad("acme")
    move_company_to_bad("acme")  # second call: no jobs left, no crash

    assert BadJob.objects.filter(company="acme").count() == 1


@pytest.mark.django_db
def test_move_company_to_bad_returns_count():
    from jobsearch.models import JobPosting

    JobPosting.objects.create(url="https://jobs.lever.co/acme/1", company="acme", title="DE 1")
    JobPosting.objects.create(url="https://jobs.lever.co/acme/2", company="acme", title="DE 2")
    JobPosting.objects.create(url="https://jobs.lever.co/other/1", company="other", title="Other")

    count = move_company_to_bad("acme")

    assert count == 2


@pytest.mark.django_db
def test_move_company_to_bad_no_match():
    count = move_company_to_bad("nonexistent")
    assert count == 0
