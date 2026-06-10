"""
Renders a BriefOS peer comparison brief as an HTML file using Jinja2.
Consumes the comparison dict from processor.compare.
"""
import logging
from datetime import datetime
from pathlib import Path

import jinja2

from briefos.config import OUTPUT_DIR

log = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Metrics where a higher raw value is better (used for best-cell highlighting).
# Keys match the row labels emitted by processor.compare.build_comparison().
_HIGHER_IS_BETTER = {
    "Market Cap", "Enterprise Value", "EPS (trailing)",
    "Operating Margin", "Net Margin", "ROE", "ROA",
    "Operating CF", "Free CF",
    "Cash & Equiv", "Equity",
}
# Metrics where a lower raw value is better
_LOWER_IS_BETTER = {
    "Trailing P/E", "Forward P/E", "Price / Book",
    "Total Debt", "CapEx",
}


def _parse_numeric(val: str) -> float | None:
    """Extract the first numeric value from a formatted string like '$1.23B' or '12.34%'."""
    import re
    m = re.search(r"-?[\d,]+\.?\d*", val.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group().replace(",", ""))
    except ValueError:
        return None


def _best_indices(sections: list[dict]) -> dict[str, int]:
    """
    Return a dict mapping metric label -> column index of the best value.
    Only labels in _HIGHER_IS_BETTER or _LOWER_IS_BETTER are evaluated.
    """
    result: dict[str, int] = {}
    for section in sections:
        for row in section["rows"]:
            label = row["label"]
            values = row["values"]
            if label in _HIGHER_IS_BETTER:
                nums = [(_parse_numeric(v), i) for i, v in enumerate(values)]
                valid = [(n, i) for n, i in nums if n is not None]
                if valid:
                    result[label] = max(valid, key=lambda x: x[0])[1]
            elif label in _LOWER_IS_BETTER:
                nums = [(_parse_numeric(v), i) for i, v in enumerate(values)]
                valid = [(n, i) for n, i in nums if n is not None and n > 0]
                if valid:
                    result[label] = min(valid, key=lambda x: x[0])[1]
    return result


def _synthesise(all_financials: list[dict]) -> list[dict]:
    """
    Assign each company one of three archetypes based on simple heuristics:
      Premium Leader  — highest forward P/E (market paying the most for growth)
      Value Play      — lowest forward P/E with positive net margins
      Growth Engine   — highest revenue
    Companies not fitting a unique slot get "Diversified".
    """
    pe_vals  = [(f.get("valuation", {}).get("pe_forward"),    i) for i, f in enumerate(all_financials)]
    rev_vals = [(f.get("income", {}).get("revenue_annual"),   i) for i, f in enumerate(all_financials)]
    nm_vals  = [(f.get("profitability", {}).get("profit_margin"), i) for i, f in enumerate(all_financials)]

    valid_pe  = [(v, i) for v, i in pe_vals  if v is not None and v > 0]
    valid_rev = [(v, i) for v, i in rev_vals if v is not None]
    valid_nm  = [(v, i) for v, i in nm_vals  if v is not None and v > 0]

    premium_idx = max(valid_pe,  key=lambda x: x[0])[1]  if valid_pe  else None
    growth_idx  = max(valid_rev, key=lambda x: x[0])[1]  if valid_rev else None
    # value = lowest P/E among companies with positive net margins
    value_candidates = [(v, i) for v, i in valid_pe if any(j == i for _, j in valid_nm)]
    value_idx = min(value_candidates, key=lambda x: x[0])[1] if value_candidates else None

    results = []
    for i, f in enumerate(all_financials):
        ticker = f["ticker"]
        name   = f["meta"].get("name", ticker)
        pe     = f.get("valuation", {}).get("pe_forward")
        nm_pct = (f.get("profitability", {}).get("profit_margin") or 0) * 100

        if i == premium_idx and i != growth_idx:
            archetype       = "Premium Leader"
            archetype_class = "premium"
            desc = (
                f"{name} commands the highest forward multiple in this peer group "
                f"({pe:.1f}x P/E), reflecting premium growth expectations."
                if pe else f"{name} commands a premium valuation in this peer group."
            )
        elif i == value_idx and i != premium_idx:
            archetype       = "Value Play"
            archetype_class = "value"
            desc = (
                f"{name} offers the most attractive entry valuation ({pe:.1f}x P/E) "
                f"with positive net margins ({nm_pct:.1f}%), a classic value profile."
                if pe else f"{name} offers a value-oriented valuation with positive profitability."
            )
        elif i == growth_idx:
            archetype       = "Growth Engine"
            archetype_class = "growth"
            rev = f.get("income", {}).get("revenue_annual") or 0
            desc = (
                f"{name} leads the peer group in scale with "
                f"${rev / 1e9:.1f}B in annual revenue."
                if rev else f"{name} leads the peer group in revenue scale."
            )
        else:
            archetype       = "Diversified"
            archetype_class = "neutral"
            desc = f"{name} sits in the middle of this peer group across valuation and profitability metrics."

        results.append({
            "ticker":         ticker,
            "name":           name,
            "archetype":      archetype,
            "archetype_class": archetype_class,
            "description":    desc,
        })
    return results


def render_comparison(comparison: dict, all_financials: list[dict] | None = None) -> Path:
    """
    Render and save a peer comparison HTML brief. Returns the output file Path.

    comparison    – dict from processor.compare.build_comparison()
    all_financials – raw financials list (needed for synthesis archetypes); optional
    """
    tickers  = comparison["tickers"]
    names    = comparison["names"]
    sections = comparison["sections"]

    ts       = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    label    = "_vs_".join(tickers)
    filename = OUTPUT_DIR / f"COMPARE_{label}_{ts}.html"

    log.info("Rendering HTML comparison for %s", " vs ".join(tickers))

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    template = env.get_template("compare.html")

    synthesis   = _synthesise(all_financials) if all_financials else []
    best_idx    = _best_indices(sections)
    timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    html = template.render(
        tickers      = tickers,
        names        = names,
        sections     = sections,
        synthesis    = synthesis,
        best_indices = best_idx,
        timestamp    = timestamp,
    )

    filename.write_text(html, encoding="utf-8")
    log.info("HTML comparison written: %s", filename)
    return filename
