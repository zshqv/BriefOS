"""
BriefOS — one-click company research brief generator.

Usage (run from project root C:\\Users\\tashu\\BriefOS\\):
    py -3.11 main.py --ticker JPM
"""
import argparse
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate a research brief PDF for a given stock ticker."
    )
    p.add_argument("--ticker", required=True, help="Stock ticker symbol, e.g. JPM")
    p.add_argument("--debug", action="store_true", help="Verbose logging")
    return p.parse_args()


def main():
    args = parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    ticker = args.ticker.strip().upper()
    log.info("BriefOS starting — ticker: %s", ticker)
    t0 = time.time()

    # ── Step 1: Fetch financials ──────────────────────────────────────────
    from briefos.fetcher.financials import fetch as fetch_financials, FinancialFetchError
    try:
        financials = fetch_financials(ticker)
    except FinancialFetchError as exc:
        log.error("Financial fetch failed: %s", exc)
        sys.exit(1)

    company_name = financials["meta"]["name"]
    log.info("Resolved company: %s", company_name)

    # ── Step 2: Fetch Wikipedia ───────────────────────────────────────────
    from briefos.fetcher.wikipedia import fetch as fetch_wiki, WikiFetchError
    try:
        wiki = fetch_wiki(company_name)
    except WikiFetchError as exc:
        log.warning("Wikipedia fetch failed (continuing without it): %s", exc)
        wiki = {"title": company_name, "summary": "", "categories": [], "url": ""}

    # ── Steps 3–4: Process + Render (stubs — wired in next steps) ─────────
    elapsed = time.time() - t0
    log.info("─" * 55)
    log.info("Fetcher layer complete in %.1fs", elapsed)
    log.info("  Company    : %s", company_name)
    log.info("  Sector     : %s", financials["meta"]["sector"])
    log.info("  Market cap : %s", financials["valuation"]["market_cap"])
    log.info("  Wikipedia  : %s", wiki["title"])
    log.info("  Wiki URL   : %s", wiki["url"])
    log.info("─" * 55)
    log.info("Processor and renderer not yet wired — coming in Step 2.")


if __name__ == "__main__":
    main()
