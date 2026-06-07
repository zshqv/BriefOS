# BriefOS

One-click company research brief generator. Pulls qualitative data from
Wikipedia and quantitative financials from yfinance, then renders a clean
timestamped PDF in under 90 seconds.

## Setup

```bash
py -3.11 -m pip install -r requirements.txt
```

## Usage

```bash
py -3.11 main.py --ticker JPM
py -3.11 main.py --ticker AAPL --debug
```

Output PDFs land in `output/` with the naming pattern:
`{TICKER}_{YYYY-MM-DD_HHMMSS}.pdf`

## Architecture

```
fetcher/     — data acquisition only (Wikipedia + yfinance)
processor/   — normalise, format, and flag the raw data
renderer/    — build and write the PDF
config.py    — all tuneable constants; nothing hardcoded in layers
```

`fetcher/financials.py` is importable standalone by PitchOS and other tools.
