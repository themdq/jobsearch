import json
import os
import random
import time
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

USER_AGENT = "job-scraper-bot/1.0"

_MAX_RETRIES = 3


def google_search(
    query: str, start: int = 1, num: int = 10, dateRestrict: str = "d7"
) -> tuple[list[dict[str, str | None]], dict]:
    """
    Returns a list of dicts with 'link', 'title', 'snippet'.
    Uses Google Custom Search API.
    start: 1-based index of first result
    num: up to 10
    """
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GOOGLE_CX = os.getenv("GOOGLE_CX")
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        raise RuntimeError("GOOGLE_API_KEY and GOOGLE_CX must be set in env")

    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": query,
        "start": start,
        "num": num,
        "dateRestrict": dateRestrict,
        "sort": "date",
        "filter": "1",
        "excludeTerms": '"Senior Data"',
        # "excludeTerms": '"Senior Analytics"',
    }
    url = "https://www.googleapis.com/customsearch/v1?" + urlencode(params)
    headers = {"User-Agent": USER_AGENT}

    for attempt in range(_MAX_RETRIES + 1):
        r = httpx.get(url, headers=headers, timeout=15)
        if r.status_code == 429 and attempt < _MAX_RETRIES:
            time.sleep(2**attempt + random.uniform(0, 1))
            continue
        r.raise_for_status()
        break

    data = r.json()
    items = data.get("items", [])
    results = []

    for it in items:
        results.append(
            {
                "link": it.get("link"),
                "title": it.get("title"),
                "snippet": it.get("snippet"),
            }
        )

    return results, data.get("queries", {})


def parse_greenhouse(url: str) -> tuple[str, str, str, str, None]:
    headers = {"User-Agent": USER_AGENT}
    r = httpx.get(url, headers=headers, timeout=15)
    r.raise_for_status()

    html = r.text
    company = url.split("/")[3]
    soup = BeautifulSoup(html, "html.parser")

    title_container = soup.find(class_="job__title")
    if title_container is None:
        raise ValueError(f"missing .job__title at {url}")
    h1 = title_container.find("h1")
    if h1 is None:
        raise ValueError(f"missing h1 in .job__title at {url}")
    title = h1.get_text(strip=True)

    location_tag = soup.find(class_="job__location")
    if location_tag is None:
        raise ValueError(f"missing .job__location at {url}")
    location = location_tag.get_text(strip=True)

    description_tag = soup.find(class_="job__description")
    if description_tag is None:
        raise ValueError(f"missing .job__description at {url}")
    description = description_tag.get_text(strip=True)

    date_posted = None
    return company, title, location, description, date_posted


def parse_lever(url: str) -> tuple[str, str, str, str, str | None]:
    headers = {"User-Agent": USER_AGENT}
    r = httpx.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    html = r.text
    company = url.split("/")[3]
    soup = BeautifulSoup(html, "html.parser")

    script = soup.find(attrs={"type": "application/ld+json"})
    if not script:
        raise ValueError(f"no application/ld+json script tag at {url}")
    try:
        script_dict = json.loads(script.text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in ld+json at {url}") from exc

    title = script_dict.get("title", "")
    temp_location = script_dict.get("jobLocation")
    if isinstance(temp_location, list):
        location = "/".join(
            loc.get("address", {}).get("addressLocality", "") for loc in temp_location
        )
    elif temp_location:
        location = temp_location.get("address", {}).get("addressLocality", "")
    else:
        location = ""

    description = script_dict.get("description", "")
    date_posted = script_dict.get("datePosted")
    return company, title, location, description, date_posted


def parse_ashby(url: str) -> tuple[str, str, str, str, str | None]:
    transport = AIOHTTPTransport(
        url="https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting"
    )
    client = Client(transport=transport)

    query = gql(
        """
        query JobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) {
    jobPosting(
        organizationHostedJobsPageName: $organizationHostedJobsPageName
        jobPostingId: $jobPostingId
    ) {
        id
        title
        departmentName
        teamNames
        locationName
        locationAddress
        workplaceType
        employmentType
        descriptionHtml
        linkedData
        isListed
        isConfidential
        publishedDate
        applicationDeadline
        secondaryLocationNames
        compensationTierSummary
        compensationTierGuideUrl
        compensationPhilosophyHtml
        scrapeableCompensationSalarySummary
        applicationLimitCalloutHtml
        shouldAskForTextingConsent
        candidateTextingPrivacyPolicyUrl
        legalEntityNameForTextingConsent
    }
}

    """
    )
    company = url.split("/")[3]
    job_id = url.split("/")[4]

    query.variable_values = {
        "organizationHostedJobsPageName": company,
        "jobPostingId": job_id,
    }
    result = client.execute(query)

    job_posting = result.get("jobPosting")
    if job_posting is None:
        raise ValueError(f"jobPosting is null for {url}")

    title = job_posting.get("title", "")
    location = job_posting.get("locationName", "")
    description = job_posting.get("descriptionHtml", "")
    linked_data = job_posting.get("linkedData") or {}
    date_posted = linked_data.get("datePosted")

    return company, title, location, description, date_posted
