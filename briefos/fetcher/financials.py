"""
Fetches quantitative financial data via yfinance.

Designed as a standalone importable module — PitchOS and any other
downstream tool can `from briefos.fetcher.financials import fetch`
without pulling in the rest of BriefOS.
"""
import logging
from typing import Optional
import yfinance as yf
from briefos.config import YF_INFO_KEYS

log = logging.getLogger(__name__)


class FinancialFetchError(Exception):
    """Raised when a ticker cannot be resolved or returns no usable data."""


def _safe(info: dict, key: str, default=None):
    """Return info[key] if present and not None, else default."""
    val = info.get(key)
    return default if val is None else val


def _income_statement(ticker: yf.Ticker) -> dict:
    """Extract trailing-twelve-month P&L highlights from the income statement."""
    try:
        df = ticker.income_stmt
        if df is None or df.empty:
            return {}
        col = df.columns[0]  # most recent annual column
        def get_row(label):
            if label in df.index:
                v = df.loc[label, col]
                return None if v != v else int(v)   # NaN guard
            return None
        return {
            "revenue_annual":       get_row("Total Revenue"),
            "gross_profit_annual":  get_row("Gross Profit"),
            "operating_income":     get_row("Operating Income"),
            "net_income_annual":    get_row("Net Income"),
            "ebit":                 get_row("EBIT"),
            "ebitda_annual":        get_row("EBITDA"),
        }
    except Exception as exc:
        log.warning("Income statement unavailable: %s", exc)
        return {}


def _balance_sheet(ticker: yf.Ticker) -> dict:
    """Extract key balance-sheet figures."""
    try:
        df = ticker.balance_sheet
        if df is None or df.empty:
            return {}
        col = df.columns[0]
        def get_row(label):
            if label in df.index:
                v = df.loc[label, col]
                return None if v != v else int(v)
            return None
        return {
            "total_assets":       get_row("Total Assets"),
            "total_liabilities":  get_row("Total Liabilities Net Minority Interest"),
            "stockholders_equity":get_row("Stockholders Equity"),
            "cash_and_equiv":     get_row("Cash And Cash Equivalents"),
            "long_term_debt":     get_row("Long Term Debt"),
        }
    except Exception as exc:
        log.warning("Balance sheet unavailable: %s", exc)
        return {}


def _cashflow(ticker: yf.Ticker) -> dict:
    """Extract operating / free cash flow."""
    try:
        df = ticker.cashflow
        if df is None or df.empty:
            return {}
        col = df.columns[0]
        def get_row(label):
            if label in df.index:
                v = df.loc[label, col]
                return None if v != v else int(v)
            return None
        return {
            "operating_cashflow": get_row("Operating Cash Flow"),
            "free_cashflow":      get_row("Free Cash Flow"),
            "capex":              get_row("Capital Expenditure"),
        }
    except Exception as exc:
        log.warning("Cash flow unavailable: %s", exc)
        return {}


def fetch(ticker_symbol: str) -> dict:
    """
    Public entry point.  Returns a structured dict with:
      meta        – company identifiers and description
      valuation   – market cap, EV, multiples
      profitability – margins and returns
      income      – annual P&L highlights
      balance     – balance sheet snapshot
      cashflow    – OCF / FCF
      market      – price, 52-week range, beta, analyst view
      dividends   – yield and payout ratio
      raw_info    – full yfinance info dict (for downstream use)

    Raises FinancialFetchError on bad tickers or no data.
    """
    symbol = ticker_symbol.strip().upper()
    log.info("yfinance: fetching '%s'", symbol)

    ticker = yf.Ticker(symbol)
    try:
        info = ticker.info
    except Exception as exc:
        raise FinancialFetchError(f"yfinance could not fetch '{symbol}': {exc}") from exc

    # A valid ticker always has a longName or shortName
    company_name: Optional[str] = (
        info.get("longName") or info.get("shortName") or ""
    )
    if not company_name:
        raise FinancialFetchError(
            f"Ticker '{symbol}' resolved to no company name — "
            "likely invalid or delisted."
        )

    income  = _income_statement(ticker)
    balance = _balance_sheet(ticker)
    cf      = _cashflow(ticker)

    return {
        "_ticker": ticker,   # yf.Ticker object — for callers that need DataFrames
        "ticker": symbol,
        "meta": {
            "name":         company_name,
            "sector":       _safe(info, "sector"),
            "industry":     _safe(info, "industry"),
            "country":      _safe(info, "country"),
            "website":      _safe(info, "website"),
            "employees":    _safe(info, "fullTimeEmployees"),
            "description":  _safe(info, "longBusinessSummary"),
            "fiscal_year_end": _safe(info, "fiscalYearEnd"),
        },
        "valuation": {
            "market_cap":       _safe(info, "marketCap"),
            "enterprise_value": _safe(info, "enterpriseValue"),
            "pe_trailing":      _safe(info, "trailingPE"),
            "pe_forward":       _safe(info, "forwardPE"),
            "price_to_book":    _safe(info, "priceToBook"),
            "price_to_sales":   _safe(info, "priceToSalesTrailingTwelveMonths"),
            "eps_trailing":     _safe(info, "trailingEps"),
            "eps_forward":      _safe(info, "forwardEps"),
        },
        "profitability": {
            "roe":              _safe(info, "returnOnEquity"),
            "roa":              _safe(info, "returnOnAssets"),
            "operating_margin": _safe(info, "operatingMargins"),
            "profit_margin":    _safe(info, "profitMargins"),
        },
        "income":   income,
        "balance":  balance,
        "cashflow": cf,
        "market": {
            "current_price":   _safe(info, "currentPrice"),
            "week52_high":     _safe(info, "fiftyTwoWeekHigh"),
            "week52_low":      _safe(info, "fiftyTwoWeekLow"),
            "beta":            _safe(info, "beta"),
            "analyst_rating":  _safe(info, "recommendationKey"),
            "analyst_count":   _safe(info, "numberOfAnalystOpinions"),
        },
        "dividends": {
            "yield":        _safe(info, "dividendYield"),
            "payout_ratio": _safe(info, "payoutRatio"),
        },
        "raw_info": info,
    }
