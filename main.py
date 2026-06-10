"""
BriefOS -- one-click company research brief generator.

Usage (run from project root C:\\Users\\tashu\\BriefOS\\):
    py -3.11 main.py --ticker JPM
    py -3.11 main.py --ticker NVDA --debug
    py -3.11 main.py --compare JPM BAC WFC
    py -3.11 main.py --compare JPM BAC WFC --debug
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
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticker",  help="Single ticker, e.g. JPM")
    group.add_argument("--compare", nargs="+", metavar="TICKER",
                       help="2-4 tickers for peer comparison, e.g. JPM BAC WFC")
    p.add_argument("--debug", action="store_true", help="Verbose logging")
    return p.parse_args()


def run_single(ticker: str):
    """Fetch, process, and render a single-ticker brief."""
    from briefos.fetcher.financials  import fetch as fetch_financials, FinancialFetchError
    from briefos.fetcher.wikipedia   import fetch as fetch_wiki,        WikiFetchError
    from briefos.fetcher.news        import fetch as fetch_news
    from briefos.processor.content  import build, compute_derived_metrics
    from briefos.processor.flags    import extract
    from briefos.charts.generator   import generate_charts
    from briefos.renderer.html      import render_brief

    try:
        financials = fetch_financials(ticker)
    except FinancialFetchError as exc:
        log.error("Financial fetch failed: %s", exc)
        sys.exit(1)

    ticker_obj   = financials["_ticker"]
    company_name = financials["meta"]["name"]
    log.info("Resolved: %s", company_name)

    try:
        wiki = fetch_wiki(company_name)
    except WikiFetchError as exc:
        log.warning("Wikipedia unavailable (continuing without it): %s", exc)
        wiki = {"title": company_name, "summary": "", "categories": [], "url": ""}

    news   = fetch_news(ticker_obj)
    log.info("News fetched -- %d headlines", len(news))

    charts = generate_charts(financials, ticker_obj)
    log.info("Charts generated")

    sections = build(financials, wiki)
    flags    = extract(financials)
    derived  = compute_derived_metrics(financials)
    log.info("Processor complete -- %d flags raised", len(flags))

    output_path = render_brief(sections, financials, flags, derived, charts, news)
    return output_path


def run_compare(tickers: list[str]):
    """Fetch all tickers and render a single comparison HTML brief."""
    from briefos.fetcher.financials   import fetch as fetch_financials, FinancialFetchError
    from briefos.processor.compare    import build_comparison
    from briefos.renderer.compare_html import render_comparison

    if len(tickers) < 2:
        log.error("--compare requires at least 2 tickers.")
        sys.exit(1)
    if len(tickers) > 4:
        log.error("--compare supports a maximum of 4 tickers.")
        sys.exit(1)

    all_financials = []
    for t in tickers:
        symbol = t.strip().upper()
        try:
            log.info("Fetching %s ...", symbol)
            financials = fetch_financials(symbol)
            all_financials.append(financials)
            log.info("Resolved: %s", financials["meta"]["name"])
        except FinancialFetchError as exc:
            log.error("Failed to fetch %s: %s", symbol, exc)
            sys.exit(1)

    comparison  = build_comparison(all_financials)
    output_path = render_comparison(comparison, all_financials)
    return output_path


def main():
    args = parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    t0 = time.time()

    if args.ticker:
        ticker = args.ticker.strip().upper()
        log.info("BriefOS starting -- ticker: %s", ticker)
        output_path = run_single(ticker)
    else:
        tickers = [t.strip().upper() for t in args.compare]
        log.info("BriefOS starting -- compare: %s", ", ".join(tickers))
        output_path = run_compare(tickers)

    elapsed = time.time() - t0
    log.info("-" * 55)
    log.info("Brief generated in %.1fs", elapsed)
    log.info("Output: %s", output_path)
    log.info("-" * 55)
    print(f"\nDone. Brief saved to:\n  {output_path}\n")


if __name__ == "__main__":
    main()
