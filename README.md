# BriefOS

**One-click company research brief generator.**  
Type a ticker. Get a structured PDF in under 90 seconds.

---

## The pain point

Before a meeting, a call, or a trade, you need a fast read on a company.
Opening Bloomberg, SEC filings, Wikipedia, and earnings pages in separate tabs
takes 20+ minutes and still leaves you stitching together a mental model.
BriefOS pulls all of it — qualitative context, quantitative financials,
analyst consensus, and notable flags — into a single clean PDF.

---

## Usage

```bash
# Install once
py -3.11 -m pip install -r requirements.txt

# Generate a brief
py -3.11 main.py --ticker JPM
py -3.11 main.py --ticker NVDA
py -3.11 main.py --ticker JNJ

# Verbose mode
py -3.11 main.py --ticker AAPL --debug
```

Output lands in `briefos/output/` as `{TICKER}_{YYYY-MM-DD_HHMMSS}.pdf`.

---

## Sample output

Running `py -3.11 main.py --ticker NVDA` produces a PDF with:

| Section | Content |
|---|---|
| **Header** | Company name, ticker, sector, country, fiscal year, timestamp |
| **Business Overview** | Lead paragraph from yfinance + Wikipedia article intro |
| **Company Profile** | Sector, industry, country, employees, website |
| **Key Flags** | Auto-detected signals — elevated P/E, strong ROE, FCF quality, beta, analyst rating |
| **Valuation** | Market cap, EV, P/E (trailing/forward), P/B, P/S, EPS |
| **Profitability** | Net margin, operating margin, ROE, ROA |
| **Income Statement** | Revenue, gross profit, operating income, net income, EBITDA (annual) |
| **Balance Sheet** | Total assets, liabilities, equity, cash, long-term debt |
| **Cash Flow** | Operating CF, free CF, capex (annual) |
| **Market Data** | Current price, 52-week range, beta, analyst rating + count |
| **Dividends** | Yield, payout ratio |
| **Tags** | Wikipedia categories (sector classification, index membership, etc.) |
| **Sources** | yfinance (Yahoo Finance) + Wikipedia article URL — timestamped |

---

## Architecture

```
BriefOS/
├── main.py               Entry point. Wires the three layers.
├── requirements.txt
└── briefos/              Python package
    ├── config.py         All tuneable constants — nothing hardcoded in layers
    ├── fetcher/
    │   ├── wikipedia.py  Qualitative data: Wikipedia search + lead-section extract
    │   └── financials.py Quantitative data: yfinance info, income, balance, cashflow
    ├── processor/
    │   ├── content.py    Normalises raw dicts into render-ready sections
    │   └── flags.py      Derives notable signals (valuation, leverage, cash, market)
    ├── renderer/
    │   └── pdf.py        Builds and writes the PDF via fpdf2
    └── output/           Generated PDFs (gitignored)
```

**Three strict layers** — fetch, process, render never call into each other.  
`fetcher/financials.py` is importable standalone by downstream tools (PitchOS, etc.):

```python
from briefos.fetcher.financials import fetch
data = fetch("AAPL")
print(data["valuation"]["market_cap"])
```

---

## Ecosystem context

BriefOS is the first module in a planned research toolkit:

| Tool | Status | Purpose |
|---|---|---|
| **BriefOS** | Live | One-click company research brief (PDF) |
| **PitchOS** | Planned | Investment pitch deck generator — reuses `briefos.fetcher.financials` |

---

## Dependencies

| Package | Purpose |
|---|---|
| `yfinance` | Quantitative financials (Yahoo Finance API) |
| `requests` | Wikipedia API HTTP calls |
| `fpdf2` | PDF generation |

---

## Limitations

- Financial data is sourced from Yahoo Finance via yfinance — subject to
  Yahoo's data quality and availability. Always verify against primary filings.
- Wikipedia article quality varies by company.
- Some metrics (e.g., P/S, dividends) return N/A for financials, banks,
  and non-dividend payers — this is expected.
