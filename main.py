"""
BriefOS — one-click company research brief generator.

Usage (run from project root C:\\Users\\tashu\\BriefOS\\):
    py -3.11 main.py --ticker JPM
    py -3.11 main.py --ticker NVDA --debug
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

    # ── Layer 1: Fetch ────────────────────────────────────────────────────
    from briefos.fetcher.financials import fetch as fetch_financials, FinancialFetchError
    from briefos.fetcher.wikipedia  import fetch as fetch_wiki,       WikiFetchError

    try:
        financials = fetch_financials(ticker)
    except FinancialFetchError as exc:
        log.error("Financial fetch failed: %s", exc)
        sys.exit(1)

    company_name = financials["meta"]["name"]
    log.info("Resolved: %s", company_name)

    try:
        wiki = fetch_wiki(company_name)
    except WikiFetchError as exc:
        log.warning("Wikipedia unavailable (continuing without it): %s", exc)
        wiki = {"title": company_name, "summary": "", "categories": [], "url": ""}

    # ── Layer 2: Process ──────────────────────────────────────────────────
    from briefos.processor.content import build
    from briefos.processor.flags   import extract

    sections = build(financials, wiki)
    flags    = extract(financials)
    log.info("Processor complete — %d flags raised", len(flags))

    # ── Layer 3: Render ───────────────────────────────────────────────────
    from briefos.renderer.pdf import render

    output_path = render(sections, flags, ticker)
    elapsed = time.time() - t0

    log.info("─" * 55)
    log.info("Brief generated in %.1fs", elapsed)
    log.info("Output: %s", output_path)
    log.info("─" * 55)
    print(f"\nDone. PDF saved to:\n  {output_path}\n")


if __name__ == "__main__":
    main()
