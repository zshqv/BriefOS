"""
Shapes raw fetcher output into render-ready sections.
No I/O, no formatting decisions — pure data transformation.
"""
from datetime import datetime
from typing import Optional


def _fmt_large(n: Optional[int], decimals: int = 2) -> str:
    """Format a large integer as $X.XXB / $X.XXM / $X.XXK."""
    if n is None:
        return "N/A"
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1e12:
        return f"{sign}${n/1e12:.{decimals}f}T"
    if n >= 1e9:
        return f"{sign}${n/1e9:.{decimals}f}B"
    if n >= 1e6:
        return f"{sign}${n/1e6:.{decimals}f}M"
    if n >= 1e3:
        return f"{sign}${n/1e3:.{decimals}f}K"
    return f"{sign}${n:,.0f}"


def _fmt_pct(v: Optional[float], decimals: int = 1) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.{decimals}f}%"


def _fmt_ratio(v: Optional[float], decimals: int = 2) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{decimals}f}x"


def _fmt_price(v: Optional[float]) -> str:
    if v is None:
        return "N/A"
    return f"${v:,.2f}"


def _fmt_employees(n: Optional[int]) -> str:
    if n is None:
        return "N/A"
    return f"{n:,}"


def _fiscal_year_label(financials: dict) -> str:
    """Return a human-readable fiscal year label, e.g. 'FY2024'."""
    month = financials["meta"].get("fiscal_year_end")
    if month:
        # fiscal_year_end is month number (1-12); derive fiscal year from today
        today = datetime.now()
        fy = today.year if today.month > month else today.year - 1
        return f"FY{fy}"
    return f"FY{datetime.now().year - 1}"


def build(financials: dict, wiki: dict) -> dict:
    """
    Transform raw fetcher dicts into a sections dict consumed by the renderer.

    Returns:
        header      – ticker, company name, timestamp, fiscal year, sources
        overview    – business description (yfinance) + Wikipedia summary
        identity    – sector, industry, employees, website, country
        valuation   – market cap, EV, and multiples table
        profitability – margin and return metrics
        income      – annual P&L highlights
        balance     – balance sheet snapshot
        cashflow    – OCF / FCF / capex
        market      – price, 52-week range, beta, analyst view
        dividends   – yield, payout ratio
        categories  – Wikipedia categories (used as tags)
    """
    fy = _fiscal_year_label(financials)
    m  = financials["meta"]
    v  = financials["valuation"]
    p  = financials["profitability"]
    i  = financials["income"]
    b  = financials["balance"]
    cf = financials["cashflow"]
    gross_profit = i.get("gross_profit_annual")
    revenue      = i.get("revenue_annual")
    gross_margin = (gross_profit / revenue) if (gross_profit and revenue and revenue != 0) else None
    mk = financials["market"]
    dv = financials["dividends"]

    description = (m.get("description") or "").strip()
    wiki_summary = (wiki.get("summary") or "").strip()

    # Prefer the yfinance long description; fall back to Wikipedia
    if len(description) < 200 and wiki_summary:
        combined_overview = wiki_summary
    elif wiki_summary and len(wiki_summary) > 100:
        # Show yfinance first, Wikipedia as additional context
        combined_overview = description
        wiki_addendum = wiki_summary
    else:
        combined_overview = description
        wiki_addendum = ""

    return {
        "header": {
            "ticker":      financials["ticker"],
            "name":        m["name"],
            "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
            "fiscal_year": fy,
            "sources":     [
                "yfinance (Yahoo Finance)",
                f"Wikipedia — {wiki.get('title', m['name'])} ({wiki.get('url', '')})",
            ],
        },
        "overview": {
            "text":        combined_overview,
            "wiki_extra":  locals().get("wiki_addendum", ""),
        },
        "identity": {
            "Sector":       m.get("sector")    or "N/A",
            "Industry":     m.get("industry")  or "N/A",
            "Country":      m.get("country")   or "N/A",
            "Employees":    _fmt_employees(m.get("employees")),
            "Website":      m.get("website")   or "N/A",
        },
        "valuation": {
            "Market Cap":        _fmt_large(v.get("market_cap")),
            "Enterprise Value":  _fmt_large(v.get("enterprise_value")),
            "Trailing P/E":      _fmt_ratio(v.get("pe_trailing")),
            "Forward P/E":       _fmt_ratio(v.get("pe_forward")),
            "Price / Book":      _fmt_ratio(v.get("price_to_book")),
            "Price / Sales":     _fmt_ratio(v.get("price_to_sales")),
            "EPS (trailing)":    _fmt_price(v.get("eps_trailing")),
            "EPS (forward)":     _fmt_price(v.get("eps_forward")),
        },
        "profitability": {
            "Gross Margin":     _fmt_pct(gross_margin),
            "Operating Margin": _fmt_pct(p.get("operating_margin")),
            "Net Margin":       _fmt_pct(p.get("profit_margin")),
            "ROE":              _fmt_pct(p.get("roe")),
            "ROA":              _fmt_pct(p.get("roa")),
        },
        "income": {
            f"Revenue ({fy})":          _fmt_large(i.get("revenue_annual")),
            f"Gross Profit ({fy})":     _fmt_large(i.get("gross_profit_annual")),
            f"Operating Income ({fy})": _fmt_large(i.get("operating_income")),
            f"Net Income ({fy})":       _fmt_large(i.get("net_income_annual")),
            f"EBITDA ({fy})":           _fmt_large(i.get("ebitda_annual")),
        },
        "balance": {
            "Total Assets":        _fmt_large(b.get("total_assets")),
            "Total Liabilities":   _fmt_large(b.get("total_liabilities")),
            "Stockholders Equity": _fmt_large(b.get("stockholders_equity")),
            "Cash & Equivalents":  _fmt_large(b.get("cash_and_equiv")),
            "Long-Term Debt":      _fmt_large(b.get("long_term_debt")),
        },
        "cashflow": {
            f"Operating CF ({fy})": _fmt_large(cf.get("operating_cashflow")),
            f"Free CF ({fy})":      _fmt_large(cf.get("free_cashflow")),
            f"CapEx ({fy})":        _fmt_large(cf.get("capex")),
        },
        "market": {
            "Current Price":    _fmt_price(mk.get("current_price")),
            "52-Week High":     _fmt_price(mk.get("week52_high")),
            "52-Week Low":      _fmt_price(mk.get("week52_low")),
            "Beta":             f"{mk['beta']:.2f}" if mk.get("beta") else "N/A",
            "Analyst Rating":   (mk.get("analyst_rating") or "N/A").upper(),
            "Analyst Count":    str(mk.get("analyst_count") or "N/A"),
        },
        "dividends": {
            "Dividend Yield":  _fmt_pct(dv.get("yield")),
            "Payout Ratio":    _fmt_pct(dv.get("payout_ratio")),
        },
        "categories": wiki.get("categories", [])[:12],
    }
