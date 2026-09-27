"""ETH Zurich official advertised doctorates. Excludes overseas campuses."""
import re
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup

SOURCE_ID = "ethz"
BASE = "https://www.jobs.ethz.ch"
LIST_URL = BASE + "/site/index"
PHD = re.compile(r"\b(ph\.?d\.?|doctoral|doctorate)\b", re.I)
OTHER = re.compile(r"post[- ]?doc|professor", re.I)


def fetch(session):
    response = session.get(LIST_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links = {}
    for a in soup.select('a[href*="/job/view/"]'):
        text = a.get_text(" ", strip=True)
        if PHD.search(text) and not OTHER.search(text):
            # Do not mislabel ETH Singapore vacancies as Swiss employment.
            if "singapore" not in text.lower():
                links[urljoin(BASE, a["href"])] = text
    jobs = []
    for url in links:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        detail = BeautifulSoup(response.text, "html.parser")
        h1 = detail.select_one("h1")
        if not h1:
            raise ValueError("ETH detail page missing title")
        title = h1.get_text(" ", strip=True)
        if not PHD.search(title) or OTHER.search(title):
            continue
        text = detail.get_text(" ", strip=True)
        jobs.append({"id": "ethz-" + url.rsplit("/", 1)[-1],
                     "source": SOURCE_ID, "source_url": url,
                     "title": title, "institution": "ETH Zurich",
                     "country": "CH", "city": "", "deadline": None,
                     "profile": "R1", "research_fields": [],
                     "description": text, "contacts": []})
        time.sleep(0.5)
    return jobs
