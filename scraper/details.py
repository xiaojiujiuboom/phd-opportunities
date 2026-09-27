"""Enrich empty job details from public pages; never bypass access restrictions."""
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def _postings(value):
    if isinstance(value, list):
        for item in value:
            yield from _postings(item)
    elif isinstance(value, dict):
        kind = value.get('@type', [])
        if kind == 'JobPosting' or isinstance(kind, list) and 'JobPosting' in kind:
            yield value
        yield from _postings(value.get('@graph', []))


def clean_html(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.select('script,style,iframe,object,embed,form,input,button,svg'):
        tag.decompose()
    allowed = {'p', 'br', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'b', 'strong', 'em', 'i', 'a', 'table', 'tr', 'th', 'td'}
    for tag in list(soup.find_all(True)):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        href = urljoin(url, tag.get('href', '')) if tag.name == 'a' and tag.get('href') else ''
        tag.attrs = {}
        if href and urlparse(href).scheme in {'http', 'https', 'mailto'}:
            tag['href'] = href
            tag['target'] = '_blank'
            tag['rel'] = 'noopener noreferrer'
    return str(soup)


def parse_details(html, url, source):
    soup = BeautifulSoup(html, 'lxml')
    posting = {}
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            posting = next(_postings(json.loads(script.get_text())), {})
        except (ValueError, TypeError):
            continue
        if posting:
            break
    body = ''
    if source == 'academics':
        body = '\n'.join(x.decode_contents() for x in soup.select('.html-content'))
    elif source == 'jobsac_uk':
        node = soup.select_one('#job-description')
        body = node.decode_contents() if node else ''
    elif source == 'euraxess':
        node = soup.select_one('.field--name-field-job-description, .field--name-body')
        body = node.decode_contents() if node else ''
    body = body or posting.get('description', '')
    result = {'description_html': clean_html(body, url)} if body else {}
    text = soup.get_text(' ', strip=True)
    posted = re.search(r'Published\s*:\s*(\d{4}-\d{2}-\d{2})', text)
    if posted or posting.get('datePosted'):
        result['posted'] = posted.group(1) if posted else str(posting['datePosted'])[:10]
    # An advert's validThrough is not necessarily the application deadline.
    deadline = re.search(r'(?:Application\s+deadline|Closing\s+date|Closes)\s*:\s*(\d{1,4}[./-]\d{1,2}[./-]\d{1,4}|\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})', text, re.I)
    if deadline:
        raw = re.sub(r'(?<=\d)(st|nd|rd|th)\b', '', deadline.group(1))
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d.%m.%Y', '%d %B %Y', '%d %b %Y'):
            try:
                result['deadline'] = datetime.strptime(raw, fmt).date().isoformat()
                break
            except ValueError:
                pass
    return result


def enrich(session, jobs, source):
    if source not in {'academics', 'jobsac_uk', 'euraxess', 'phdgermany'}:
        return {}
    counts = {'attempted': 0, 'with_description': 0, 'unavailable': 0}
    for job in jobs:
        if job.get('description_html') or job.get('description'):
            continue
        counts['attempted'] += 1
        response = None
        try:
            response = session.get(job['source_url'], timeout=20)
            response.raise_for_status()
            detail = parse_details(response.text, job['source_url'], source)
            job.update(detail)
            job['details_checked_at'] = datetime.now(timezone.utc).isoformat()
            if detail.get('description_html'):
                counts['with_description'] += 1
            else:
                counts['unavailable'] += 1
            if counts['attempted'] % 25 == 0:
                print(f'[{source}] details {counts}', flush=True)
        except Exception:
            counts['unavailable'] += 1
            # Stop promptly on rate limiting or access denial, preserving original links.
            if response is not None and response.status_code in {403, 429}:
                break
        finally:
            time.sleep(0.4)
    return counts
