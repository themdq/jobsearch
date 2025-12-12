import json
import os
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

USER_AGENT = "job-scraper-bot/1.0"


def google_search(query, start=1, num=10, dateRestrict="d7"):
    """
    Возвращает список dict с 'link', 'title', 'snippet'
    Uses Google Custom Search API.
    start: 1-based index of first result
    num: up to 10
    """
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

    r = httpx.get(url, headers=headers, timeout=15)
    r.raise_for_status()
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


def parse_greenhouse(url):
    headers = {"User-Agent": USER_AGENT}
    r = httpx.get(url, headers=headers, timeout=15)
    r.raise_for_status()

    html = r.text
    company = url.split("/")[3]
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find(class_="job__title")

    h1 = title.find("h1")
    title = h1.text
    location = soup.find(class_="job__location")
    location = location.text
    description = soup.find(class_="job__description")
    description = description.text
    date_posted = None

    if any([description, title, location]) is None:
        raise Exception("Problem with link")

    return company, title, location, description, date_posted


def parse_lever(url):
    headers = {"User-Agent": USER_AGENT}
    r = httpx.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    html = r.text
    company = url.split("/")[3]
    soup = BeautifulSoup(html, "html.parser")

    script = soup.find(attrs={"type": "application/ld+json"})
    if script:
        script_dict = json.loads(script.text)
        title = script_dict["title"]
        temp_location = script_dict["jobLocation"]
        if isinstance(temp_location, list):
            location = []
            for loc in temp_location:
                location.append(loc["address"]["addressLocality"])
            location = "/".join(location)
        else:
            location = temp_location["address"]["addressLocality"]

        description = script_dict["description"]
        date_posted = script_dict["datePosted"]
    return company, title, location, description, date_posted


def parse_ashby(url):
    # Select your transport with a defined url endpoint
    transport = AIOHTTPTransport(
        url="https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting"
    )

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport)

    # Provide a GraphQL query
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
    # Execute the query on the transport
    result = client.execute(query)
    title = result["jobPosting"]["title"]
    location = result["jobPosting"]["locationName"]
    description = result["jobPosting"]["descriptionHtml"]
    date_posted = result["jobPosting"]["linkedData"]["datePosted"]
    return company, title, location, description, date_posted
