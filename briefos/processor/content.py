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


def _safe_div(numerator, denominator):
    """Return numerator / denominator, or None if either is None or denominator is zero."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _fiscal_year_label(financials: dict) -> str:
    """
    Return the most recently completed fiscal year label, e.g. 'FY2025'.

    Logic:
      - fiscal_year_end from yfinance is the month number the FY ends (1-12).
      - If that month has already passed this calendar year, the completed
        FY carries the current calendar year label.
      - If that month is still upcoming this calendar year, the most recently
        completed FY ended last calendar year.
      - Falls back to FY(current year - 1) if no fiscal_year_end is available.

    Examples (assuming today is June 2026):
      December FY (month 12) -> month 12 not yet passed -> FY2025
      September FY (month 9)  -> month 9 not yet passed -> FY2025
      March FY (month 3)      -> month 3 has passed     -> FY2026
    """
    month = financials["meta"].get("fiscal_year_end")
    today = datetime.now()

    if not month:
        return f"FY{today.year - 1}"

    # If the fiscal year end month has already passed this calendar year,
    # the most recently completed fiscal year carries this calendar year's label
    if today.month > month:
        return f"FY{today.year}"
    else:
        return f"FY{today.year - 1}"


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
    wiki_addendum = ""

    if len(description) < 200 and wiki_summary:
        combined_overview = wiki_summary
    elif wiki_summary and len(wiki_summary) > 100:
        # Show yfinance first, Wikipedia as additional context
        combined_overview = description
        wiki_addendum     = wiki_summary
    else:
        combined_overview = description

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
            "text":       combined_overview,
            "wiki_extra": wiki_addendum,
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


def compute_derived_metrics(financials: dict) -> dict:
    """
    Compute analyst-style derived metrics from the dict returned by
    briefos.fetcher.financials.fetch().

    Returns:
      quality_of_earnings  – {"ratio": float, "flag": "Strong"/"Weak"} or {"ratio": None, "flag": None}
      net_cash_position    – "Net Cash: $X.XB" / "Net Debt: $X.XB", or None
      capex_intensity      – abs(CapEx) / Revenue as a %, or None
      fcf_yield_pct        – Free Cash Flow / Market Cap as a %, or None
      margin_spread        – Gross Margin % minus Operating Margin %, or None
      executive_takeaway   – one-sentence template summary string

    Never raises — all values fall back to None on missing inputs.
    """
    cf = financials.get("cashflow", {})
    i  = financials.get("income", {})
    b  = financials.get("balance", {})
    v  = financials.get("valuation", {})
    p  = financials.get("profitability", {})
    m  = financials.get("meta", {})

    ocf          = cf.get("operating_cashflow")
    net_income   = i.get("net_income_annual")
    fcf          = cf.get("free_cashflow")
    capex        = cf.get("capex")
    revenue      = i.get("revenue_annual")
    gross_profit = i.get("gross_profit_annual")
    cash         = b.get("cash_and_equiv")
    ltdebt       = b.get("long_term_debt")
    mktcap       = v.get("market_cap")
    op_margin    = p.get("operating_margin")   # decimal, e.g. 0.25 = 25 %
    fwd_pe       = v.get("pe_forward")
    net_margin   = p.get("profit_margin")       # decimal, e.g. 0.21 = 21 %

    # 1. Quality of earnings — OCF / Net Income
    qoe_ratio = _safe_div(ocf, net_income)
    qoe_flag  = ("Strong" if qoe_ratio >= 0.8 else "Weak") if qoe_ratio is not None else None

    # 2. Net cash position — Cash minus Long-Term Debt
    if cash is not None and ltdebt is not None:
        net_cash = cash - ltdebt
        if net_cash >= 0:
            net_cash_label = f"Net Cash: ${net_cash / 1e9:.1f}B"
        else:
            net_cash_label = f"Net Debt: ${abs(net_cash) / 1e9:.1f}B"
    else:
        net_cash_label = None

    # 3. CapEx intensity — abs(CapEx) / Revenue (yfinance stores CapEx as negative)
    raw_capex_intensity = _safe_div(None if capex is None else abs(capex), revenue)
    capex_intensity     = round(raw_capex_intensity * 100, 2) if raw_capex_intensity is not None else None

    # 4. FCF yield — Free Cash Flow / Market Cap
    raw_fcf_yield = _safe_div(fcf, mktcap)
    fcf_yield_pct = round(raw_fcf_yield * 100, 2) if raw_fcf_yield is not None else None

    # 5. Margin spread — Gross Margin % minus Operating Margin % (SG&A drag proxy)
    gross_margin_pct = _safe_div(gross_profit, revenue)
    gross_margin_pct = (gross_margin_pct * 100) if gross_margin_pct is not None else None
    op_margin_pct    = (op_margin * 100) if op_margin is not None else None
    if gross_margin_pct is not None and op_margin_pct is not None:
        margin_spread = round(gross_margin_pct - op_margin_pct, 2)
    else:
        margin_spread = None

    # 6. Executive takeaway — template-driven one-liner
    name   = m.get("name") or financials.get("ticker", "This company")
    sector = m.get("sector") or "diversified"
    pe_str = f"{fwd_pe:.1f}" if fwd_pe is not None else "N/A"
    nm_str = f"{net_margin * 100:.1f}" if net_margin is not None else "N/A"
    q_str  = qoe_flag or "mixed"
    executive_takeaway = (
        f"{name} is a {sector} company trading at {pe_str}x forward earnings "
        f"with {nm_str}% net margins and a {q_str} earnings quality profile."
    )

    return {
        "quality_of_earnings": {"ratio": round(qoe_ratio, 2) if qoe_ratio is not None else None, "flag": qoe_flag},
        "net_cash_position":   net_cash_label,
        "capex_intensity":     capex_intensity,
        "fcf_yield_pct":       fcf_yield_pct,
        "margin_spread":       margin_spread,
        "executive_takeaway":  executive_takeaway,
    }
