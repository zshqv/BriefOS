"""
Derives notable flags from processed financial data.
Returns a list of (severity, label, detail) tuples for the renderer.

Severity levels: "positive", "caution", "alert"
"""
from typing import Optional


def _raw(financials: dict, *path: str):
    """Safe nested get from the raw financials dict."""
    obj = financials
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


# Sectors where standard leverage and FCF flags are not meaningful
_FINANCIAL_SECTORS = {
    "financial services", "banking", "insurance",
    "capital markets", "asset management", "diversified financials"
}

def _is_financial(financials: dict) -> bool:
    """Return True if the company is in a financial sector."""
    sector = (_raw(financials, "meta", "sector") or "").lower()
    return any(s in sector for s in _FINANCIAL_SECTORS)


def _check_valuation(financials: dict, flags: list):
    pe = _raw(financials, "valuation", "pe_trailing")
    if pe is not None:
        if pe > 50:
            flags.append(("caution", "Elevated P/E", f"Trailing P/E of {pe:.1f}x is above 50 — implies high growth expectations."))
        elif pe < 0:
            flags.append(("alert", "Negative Earnings", f"Trailing P/E is negative ({pe:.1f}x) — company is unprofitable on a trailing basis."))
        elif pe < 12:
            flags.append(("positive", "Low P/E", f"Trailing P/E of {pe:.1f}x is below 12 — may indicate undervaluation."))

    pb = _raw(financials, "valuation", "price_to_book")
    if pb is not None and pb < 1.0 and pb > 0:
        flags.append(("positive", "Below Book Value", f"P/B of {pb:.2f}x — trading below tangible book value."))


def _check_profitability(financials: dict, flags: list):
    margin = _raw(financials, "profitability", "profit_margin")
    if margin is not None:
        if margin < 0:
            flags.append(("alert", "Net Loss", f"Net profit margin is {margin*100:.1f}% — company is running at a loss."))
        elif margin > 0.25:
            flags.append(("positive", "High Net Margin", f"Net margin of {margin*100:.1f}% — exceptionally profitable."))

    roe = _raw(financials, "profitability", "roe")
    if roe is not None:
        if roe > 0.30:
            flags.append(("positive", "Strong ROE", f"Return on equity of {roe*100:.1f}% — highly efficient capital use."))
        elif roe < 0:
            flags.append(("alert", "Negative ROE", f"ROE of {roe*100:.1f}% — equity is being eroded."))


def _check_cashflow(financials: dict, flags: list):
    fcf = _raw(financials, "cashflow", "free_cashflow")
    rev = _raw(financials, "income", "revenue_annual")

    if fcf is not None:
        if fcf < 0:
            flags.append(("caution", "Negative Free Cash Flow",
                "FCF is negative -- company is consuming more cash than it generates."))
        elif not _is_financial(financials) and rev and rev > 0 and (fcf / rev) > 0.20:
            flags.append(("positive", "Strong FCF Yield",
                f"FCF / Revenue = {fcf/rev*100:.1f}% -- high-quality cash generation."))


def _check_leverage(financials: dict, flags: list):
    if _is_financial(financials):
        # For banks, high D/E is structural — flag it as context, not alert
        debt   = _raw(financials, "balance", "long_term_debt")
        equity = _raw(financials, "balance", "stockholders_equity")
        if debt and equity and equity > 0:
            de = debt / equity
            if de > 5.0:
                flags.append(("caution", "High Leverage (Financial Sector)",
                    f"Debt/Equity of {de:.1f}x -- note: elevated leverage is "
                    f"structurally normal for banks and financial institutions."))
        return

    # Non-financial leverage checks (unchanged)
    debt   = _raw(financials, "balance", "long_term_debt")
    equity = _raw(financials, "balance", "stockholders_equity")
    ebitda = _raw(financials, "income", "ebitda_annual")

    if debt and equity and equity > 0:
        de = debt / equity
        if de > 3.0:
            flags.append(("alert", "High Leverage",
                f"Debt/Equity of {de:.1f}x -- significant financial leverage."))

    if debt and ebitda and ebitda > 0:
        net_debt_ebitda = debt / ebitda
        if net_debt_ebitda > 4.0:
            flags.append(("caution", "Heavy Debt Load",
                f"Debt/EBITDA of {net_debt_ebitda:.1f}x -- debt repayment may constrain growth."))


def _check_market(financials: dict, flags: list):
    beta = _raw(financials, "market", "beta")
    if beta is not None:
        if beta > 1.5:
            flags.append(("caution", "High Beta", f"Beta of {beta:.2f} — significantly more volatile than the market."))
        elif beta < 0.5:
            flags.append(("positive", "Low Beta", f"Beta of {beta:.2f} — defensive, low-volatility stock."))

    rating = _raw(financials, "market", "analyst_rating")
    count  = _raw(financials, "market", "analyst_count")
    if rating and count and count >= 5:
        if rating in ("buy", "strong_buy"):
            flags.append(("positive", "Analyst Consensus: Buy", f"{count} analysts rate this a {rating.replace('_', ' ').title()}."))
        elif rating in ("sell", "strong_sell", "underperform"):
            flags.append(("alert", "Analyst Consensus: Sell", f"{count} analysts rate this a {rating.replace('_', ' ').title()}."))


def _check_financial_health(financials: dict, flags: list):
    """Bank-specific flags — only runs for financial sector tickers."""
    if not _is_financial(financials):
        return

    # Net Interest Margin proxy: not directly available via yfinance
    # so we flag analyst rating with extra weight for banks
    rating = _raw(financials, "market", "analyst_rating")
    count  = _raw(financials, "market", "analyst_count")
    roe    = _raw(financials, "profitability", "roe")

    if roe is not None:
        if roe > 0.12:
            flags.append(("positive", "Strong Bank ROE",
                f"ROE of {roe*100:.1f}% -- above 12% threshold considered strong for banks."))
        elif roe < 0.06:
            flags.append(("caution", "Weak Bank ROE",
                f"ROE of {roe*100:.1f}% -- below 6% suggests capital inefficiency for a bank."))

    # Price to Book is especially meaningful for banks
    pb = _raw(financials, "valuation", "price_to_book")
    if pb is not None:
        if pb < 1.0 and pb > 0:
            flags.append(("caution", "Trading Below Book (Bank)",
                f"P/B of {pb:.2f}x -- for a bank this may signal market concerns "
                f"about asset quality or profitability."))
        elif pb > 2.5:
            flags.append(("positive", "Premium Bank Valuation",
                f"P/B of {pb:.2f}x -- market pricing in strong franchise value."))


def extract(financials: dict) -> list[tuple[str, str, str]]:
    """
    Public entry point.
    Returns a list of (severity, label, detail) tuples, sorted alert → caution → positive.
    """
    flags: list[tuple[str, str, str]] = []
    _check_valuation(financials, flags)
    _check_profitability(financials, flags)
    _check_cashflow(financials, flags)
    _check_leverage(financials, flags)
    _check_market(financials, flags)
    _check_financial_health(financials, flags)   # ← add this line

    order = {"alert": 0, "caution": 1, "positive": 2}
    return sorted(flags, key=lambda f: order.get(f[0], 9))
