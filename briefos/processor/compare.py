"""
Builds a comparison table from multiple fetched financials dicts.
Used by the --compare flow in main.py.
"""
from briefos.processor.content import (
    _fmt_large, _fmt_pct, _fmt_ratio, _fmt_price
)


def build_comparison(all_financials: list[dict]) -> dict:
    """
    Takes a list of financials dicts (one per ticker) and returns
    a comparison dict structured as:
      tickers   — list of ticker symbols
      names     — list of company names
      sections  — ordered list of (section_label, [ {metric: value, ...} ])

    Each inner dict maps metric label -> formatted string, one per ticker.
    """
    tickers = [f["ticker"] for f in all_financials]
    names   = [f["meta"]["name"] for f in all_financials]

    def row(label, values):
        return {"label": label, "values": values}

    def get_val(f, *path):
        obj = f
        for key in path:
            if not isinstance(obj, dict):
                return None
            obj = obj.get(key)
        return obj

    sections = [
        {
            "title": "Company Profile",
            "rows": [
                row("Sector",    [get_val(f, "meta", "sector")    or "N/A" for f in all_financials]),
                row("Country",   [get_val(f, "meta", "country")   or "N/A" for f in all_financials]),
                row("Employees", [f"{get_val(f, 'meta', 'employees'):,}" if get_val(f, 'meta', 'employees') else "N/A" for f in all_financials]),
            ]
        },
        {
            "title": "Valuation",
            "rows": [
                row("Market Cap",       [_fmt_large(get_val(f, "valuation", "market_cap"))       for f in all_financials]),
                row("Enterprise Value", [_fmt_large(get_val(f, "valuation", "enterprise_value")) for f in all_financials]),
                row("Trailing P/E",     [_fmt_ratio(get_val(f, "valuation", "pe_trailing"))      for f in all_financials]),
                row("Forward P/E",      [_fmt_ratio(get_val(f, "valuation", "pe_forward"))       for f in all_financials]),
                row("Price / Book",     [_fmt_ratio(get_val(f, "valuation", "price_to_book"))    for f in all_financials]),
                row("EPS (trailing)",   [_fmt_price(get_val(f, "valuation", "eps_trailing"))     for f in all_financials]),
            ]
        },
        {
            "title": "Profitability",
            "rows": [
                row("Operating Margin", [_fmt_pct(get_val(f, "profitability", "operating_margin")) for f in all_financials]),
                row("Net Margin",       [_fmt_pct(get_val(f, "profitability", "profit_margin"))    for f in all_financials]),
                row("ROE",              [_fmt_pct(get_val(f, "profitability", "roe"))              for f in all_financials]),
                row("ROA",              [_fmt_pct(get_val(f, "profitability", "roa"))              for f in all_financials]),
            ]
        },
        {
            "title": "Market Data",
            "rows": [
                row("Current Price", [_fmt_price(get_val(f, "market", "current_price")) for f in all_financials]),
                row("52-Week High",  [_fmt_price(get_val(f, "market", "week52_high"))   for f in all_financials]),
                row("52-Week Low",   [_fmt_price(get_val(f, "market", "week52_low"))    for f in all_financials]),
                row("Beta",          [f"{get_val(f, 'market', 'beta'):.2f}" if get_val(f, 'market', 'beta') else "N/A" for f in all_financials]),
                row("Analyst Rating",[( get_val(f, "market", "analyst_rating") or "N/A").upper() for f in all_financials]),
            ]
        },
        {
            "title": "Balance Sheet",
            "rows": [
                row("Total Assets",   [_fmt_large(get_val(f, "balance", "total_assets"))        for f in all_financials]),
                row("Total Debt",     [_fmt_large(get_val(f, "balance", "long_term_debt"))       for f in all_financials]),
                row("Cash & Equiv",   [_fmt_large(get_val(f, "balance", "cash_and_equiv"))       for f in all_financials]),
                row("Equity",         [_fmt_large(get_val(f, "balance", "stockholders_equity"))  for f in all_financials]),
            ]
        },
        {
            "title": "Cash Flow",
            "rows": [
                row("Operating CF", [_fmt_large(get_val(f, "cashflow", "operating_cashflow")) for f in all_financials]),
                row("Free CF",      [_fmt_large(get_val(f, "cashflow", "free_cashflow"))      for f in all_financials]),
                row("CapEx",        [_fmt_large(get_val(f, "cashflow", "capex"))              for f in all_financials]),
            ]
        },
    ]

    return {
        "tickers": tickers,
        "names":   names,
        "sections": sections,
    }
