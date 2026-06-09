# Changelog

All notable changes to BriefOS are documented here.

## [1.1.0] - 2026-06-09

### Added
- `--compare` mode: generate a single landscape A4 peer comparison PDF
  for 2-4 tickers (`py -3.11 main.py --compare JPM BAC WFC`)
- `briefos/processor/compare.py`: builds side-by-side comparison dict
  from multiple financials fetches
- `briefos/renderer/compare_pdf.py`: renders comparison PDF with
  per-section metric rows and company header columns
- Sector-aware flags engine: financial sector tickers (banks, insurance,
  capital markets) now receive bank-specific ROE and P/B flags instead
  of misleading D/E and EBITDA leverage alerts

### Fixed
- Gross margin now computed correctly from gross_profit / revenue;
  previously both Gross Margin and Net Margin showed the same figure
- `wiki_addendum` replaced fragile `locals().get()` with explicit
  variable initialisation
- Flags block row alignment: Y position is now anchored before drawing
  each row so multi_cell wrapping no longer displaces subsequent flags
- Fiscal year label logic corrected for non-December fiscal year ends

### Changed
- `requirements.txt` pinned to exact versions: yfinance==1.3.0,
  fpdf2==2.8.7, requests==2.34.2

## [1.0.0] - 2026-06-08

### Added
- Initial release: single-ticker research brief generator
- Three-layer architecture: fetch → process → render
- `briefos/fetcher/financials.py`: yfinance data fetch, importable
  standalone by downstream tools
- `briefos/fetcher/wikipedia.py`: Wikipedia API qualitative context
- `briefos/processor/content.py`: normalises raw data into
  render-ready sections
- `briefos/processor/flags.py`: derives notable signals across
  valuation, profitability, cashflow, leverage, and market data
- `briefos/renderer/pdf.py`: fpdf2-based PDF with navy accent theme
- `briefos/config.py`: all tuneable constants centralised
- `--debug` flag for verbose logging
- Graceful Wikipedia fallback when article unavailable
