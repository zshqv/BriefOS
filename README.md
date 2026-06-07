# BriefOS

One-click company research brief generator. Pulls qualitative data from
Wikipedia and quantitative financials from yfinance, then renders a clean
timestamped PDF in under 90 seconds.

## Setup

```bash
cd C:\Users\tashu\BriefOS
py -3.11 -m pip install -r requirements.txt
```

## Usage

```bash
py -3.11 main.py --ticker JPM
py -3.11 main.py --ticker AAPL --debug
```

Output PDFs land in `briefos/output/` with the naming pattern:
`{TICKER}_{YYYY-MM-DD_HHMMSS}.pdf`

## Project layout

```
BriefOS\
├── main.py              ← entry point (run from here)
├── requirements.txt
├── README.md
└── briefos\             ← Python package
    ├── config.py        ← all tuneable constants
    ├── fetcher\
    │   ├── wikipedia.py ← qualitative data (Wikipedia API)
    │   └── financials.py← quantitative data (yfinance) — reusable by PitchOS
    ├── processor\       ← normalise, format, flag raw data
    ├── renderer\        ← build and write the PDF
    └── output\          ← generated PDFs land here
```

## Architecture rules

1. **Three strict layers** — fetch, process, render never bleed into each other.
2. **Wikipedia resolution** uses the yfinance `longName`, not the raw ticker.
3. **`financials.py`** is an importable module: `from briefos.fetcher.financials import fetch`.
4. **Graceful failure** — bad tickers or failed fetches exit cleanly with a log message.
5. Every PDF carries a timestamp, fiscal year reference, and named sources.
