"""
Fetches qualitative company data from the Wikipedia free API.

Resolution strategy: use the company's longName from yfinance as the
search query — more reliable than the raw ticker against Wikipedia's
title index.
"""
import logging
import requests
from typing import Optional
from briefos.config import WIKI_API_URL, WIKI_SUMMARY_CHARS, WIKI_REQUEST_TIMEOUT

log = logging.getLogger(__name__)

# Wikipedia blocks requests with default User-Agent; use an informative one
_HEADERS = {
    "User-Agent": "BriefOS/1.0 (company research tool; https://github.com/briefos) python-requests"
}


class WikiFetchError(Exception):
    """Raised when Wikipedia data cannot be retrieved."""


def _search_page_title(company_name: str) -> Optional[str]:
    """Return the best-matching Wikipedia page title for a company name."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": company_name,
        "srlimit": 5,
        "srnamespace": 0,
        "format": "json",
    }
    resp = requests.get(WIKI_API_URL, params=params, headers=_HEADERS, timeout=WIKI_REQUEST_TIMEOUT)
    resp.raise_for_status()
    results = resp.json().get("query", {}).get("search", [])
    if not results:
        return None
    # Prefer an exact-name match; fall back to the top result
    name_lower = company_name.lower()
    for r in results:
        if name_lower in r["title"].lower():
            return r["title"]
    return results[0]["title"]


def _fetch_page_summary(title: str) -> dict:
    """Fetch the page intro (lead) and categories for a given title."""
    params = {
        "action": "query",
        "prop": "extracts|categories|info",
        "titles": title,
        "exintro": True,
        "explaintext": True,
        "inprop": "url",
        "cllimit": 20,
        "format": "json",
        "redirects": 1,
    }
    resp = requests.get(WIKI_API_URL, params=params, headers=_HEADERS, timeout=WIKI_REQUEST_TIMEOUT)
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    if "missing" in page:
        raise WikiFetchError(f"Page '{title}' not found on Wikipedia.")
    return page


def fetch(company_name: str) -> dict:
    """
    Public entry point.  Returns a dict with:
      title       – resolved Wikipedia article title
      summary     – truncated lead-section text
      categories  – list of category strings
      url         – full Wikipedia URL
    Raises WikiFetchError on any unrecoverable failure.
    """
    log.info("Wikipedia: searching for '%s'", company_name)
    title = _search_page_title(company_name)
    if not title:
        raise WikiFetchError(
            f"No Wikipedia article found for '{company_name}'."
        )
    log.info("Wikipedia: resolved to page '%s'", title)

    page = _fetch_page_summary(title)
    raw_text = page.get("extract", "")
    summary  = raw_text[:WIKI_SUMMARY_CHARS].strip()
    if len(raw_text) > WIKI_SUMMARY_CHARS:
        # truncate at the last sentence boundary inside the limit
        cut = summary.rfind(". ")
        if cut > 200:
            summary = summary[: cut + 1]

    categories = [
        c["title"].replace("Category:", "")
        for c in page.get("categories", [])
        if not c["title"].startswith("Category:Articles")
    ]

    url = page.get("fullurl", f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}")

    return {
        "title":      title,
        "summary":    summary,
        "categories": categories,
        "url":        url,
    }
