"""
Central configuration for BriefOS.
All tuneable constants live here — nothing hardcoded in layers.
"""
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Wikipedia ────────────────────────────────────────────────────────────────
WIKI_API_URL      = "https://en.wikipedia.org/w/api.php"
WIKI_SUMMARY_CHARS = 3000   # max chars to keep from the lead section
WIKI_REQUEST_TIMEOUT = 15   # seconds

# ── yfinance ────────────────────────────────────────────────────────────────
YF_INFO_KEYS = [
    "longName", "sector", "industry", "country", "website",
    "fullTimeEmployees", "marketCap", "enterpriseValue",
    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailingTwelveMonths",
    "trailingEps", "forwardEps",
    "totalRevenue", "grossProfits", "ebitda", "netIncomeToCommon",
    "totalDebt", "totalCash", "operatingCashflow", "freeCashflow",
    "returnOnEquity", "returnOnAssets", "operatingMargins", "profitMargins",
    "dividendYield", "payoutRatio",
    "beta", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "currentPrice",
    "recommendationKey", "numberOfAnalystOpinions",
    "longBusinessSummary",
    "fiscalYearEnd",
]

# ── PDF ──────────────────────────────────────────────────────────────────────
PDF_MARGIN_MM   = 18
PDF_FONT_FAMILY = "Helvetica"
PDF_ACCENT_HEX  = "#1B4F72"   # dark navy — adjustable without touching renderer

# ── Runtime ──────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 20          # generic fallback for any HTTP call
MAX_RETRIES     = 2
