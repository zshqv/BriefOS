"""
Fetches recent news headlines via a yfinance Ticker object.

Designed as a standalone importable module — callers pass an already-created
Ticker so the module never constructs one itself.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
import yfinance as yf

log = logging.getLogger(__name__)

_MAX_HEADLINES = 7
_DATE_FORMAT = "%d %b %Y"


def _format_date(raw) -> Optional[str]:
    """Convert a Unix timestamp (int/float) or None to '10 Jun 2026' format."""
    if raw is None:
        return None
    try:
        return datetime.fromtimestamp(int(raw), tz=timezone.utc).strftime(_DATE_FORMAT)
    except Exception as exc:
        log.warning("Could not parse published date '%s': %s", raw, exc)
        return None


def fetch(ticker: yf.Ticker) -> list[dict]:
    """
    Public entry point.  Returns a list of up to 7 headline dicts, each with:
      title          – article headline
      publisher      – outlet name
      published_date – human-readable date string ('10 Jun 2026')
      link           – canonical article URL

    Returns an empty list if .news is unavailable or raises — never crashes.
    """
    log.info("yfinance: fetching news for ticker")
    try:
        items = ticker.news
    except Exception as exc:
        log.warning("News fetch failed: %s", exc)
        return []

    if not items:
        return []

    results = []
    for item in items[:_MAX_HEADLINES]:
        try:
            content = item.get("content", {}) if isinstance(item, dict) else {}
            title      = content.get("title") or item.get("title")
            publisher  = (
                content.get("provider", {}).get("displayName")
                or item.get("publisher")
            )
            pub_date   = (
                content.get("pubDate")
                or item.get("providerPublishTime")
            )
            link       = (
                content.get("canonicalUrl", {}).get("url")
                or item.get("link")
            )

            # pubDate may arrive as epoch int or an ISO string from newer yfinance
            if isinstance(pub_date, str):
                try:
                    dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    formatted_date = dt.strftime(_DATE_FORMAT)
                except Exception:
                    formatted_date = None
            else:
                formatted_date = _format_date(pub_date)

            results.append({
                "title":          title,
                "publisher":      publisher,
                "published_date": formatted_date,
                "link":           link,
            })
        except Exception as exc:
            log.warning("Skipping malformed news item: %s", exc)

    return results
