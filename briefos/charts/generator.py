"""
Generates base64-encoded PNG chart images from financial data.

Requires a yf.Ticker alongside the financials dict so multi-year income
statement DataFrames can be fetched without a redundant network round-trip.
Uses the Agg backend — safe for headless / server environments.
"""
import base64
import io
import logging
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import yfinance as yf

log = logging.getLogger(__name__)

# --- palette & typography -------------------------------------------------
_NAVY  = "#1B2A4A"
_SLATE = "#64748B"
_AMBER = "#D97706"

plt.rcParams["font.family"]     = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Segoe UI", "Arial", "Helvetica", "DejaVu Sans"]

_MAX_YEARS = 5


# --- shared helpers -------------------------------------------------------

def _fig_and_ax():
    """Return a (fig, ax) pair with transparent background and clean spines."""
    fig, ax = plt.subplots(figsize=(7, 3.5))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")
    ax.yaxis.grid(True, linestyle="--", alpha=0.3, color="#94A3B8")
    ax.set_axisbelow(True)
    return fig, ax


def _to_b64(fig) -> str:
    """Serialise a matplotlib figure to a base64 PNG string, then close it."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=130, transparent=True)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _fy_label(ts) -> str:
    """Convert a pandas Timestamp column header to 'FY2023'."""
    try:
        return f"FY{ts.year}"
    except Exception:
        return str(ts)


def _billions(x, _):
    return f"${x / 1e9:.1f}B"


def _percent(x, _):
    return f"{x:.1f}%"


def _load_stmt(ticker: yf.Ticker):
    """
    Return income_stmt with columns in chronological order (oldest first),
    or None if unavailable.
    """
    try:
        df = ticker.income_stmt
        if df is None or df.empty:
            return None
        return df[df.columns[::-1]]   # yfinance returns most-recent-first
    except Exception as exc:
        log.warning("Could not load income_stmt: %s", exc)
        return None


# --- individual chart builders --------------------------------------------

def _revenue_trend(df) -> Optional[str]:
    """Bar chart of annual total revenue."""
    try:
        row = "Total Revenue"
        if row not in df.index:
            log.warning("'%s' not in income_stmt", row)
            return None

        series = df.loc[row].dropna().iloc[-_MAX_YEARS:]
        if series.empty:
            return None

        labels = [_fy_label(c) for c in series.index]
        values = series.values.astype(float)

        fig, ax = _fig_and_ax()
        ax.bar(labels, values, color=_NAVY, width=0.55, zorder=3)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_billions))
        ax.set_title(
            f"Revenue Trend ({labels[0]}–{labels[-1]})",
            fontsize=11, fontweight="bold", color="#1E293B", pad=10,
        )
        ax.tick_params(axis="both", labelsize=9, colors="#475569")
        fig.tight_layout()
        return _to_b64(fig)
    except Exception as exc:
        log.warning("Revenue trend chart failed: %s", exc)
        return None


def _net_income_trend(df) -> Optional[str]:
    """Bar chart of annual net income; negative bars rendered in amber."""
    try:
        row = "Net Income"
        if row not in df.index:
            log.warning("'%s' not in income_stmt", row)
            return None

        series = df.loc[row].dropna().iloc[-_MAX_YEARS:]
        if series.empty:
            return None

        labels = [_fy_label(c) for c in series.index]
        values = series.values.astype(float)
        colors = [_AMBER if v < 0 else _NAVY for v in values]

        fig, ax = _fig_and_ax()
        ax.bar(labels, values, color=colors, width=0.55, zorder=3)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_billions))
        ax.axhline(0, color="#CBD5E1", linewidth=0.8)
        ax.set_title(
            f"Net Income Trend ({labels[0]}–{labels[-1]})",
            fontsize=11, fontweight="bold", color="#1E293B", pad=10,
        )
        ax.tick_params(axis="both", labelsize=9, colors="#475569")
        fig.tight_layout()
        return _to_b64(fig)
    except Exception as exc:
        log.warning("Net income trend chart failed: %s", exc)
        return None


def _margin_evolution(df) -> Optional[str]:
    """Line chart of gross, operating, and net margin % across fiscal years."""
    try:
        revenue_row = "Total Revenue"
        if revenue_row not in df.index:
            log.warning("'%s' not in income_stmt", revenue_row)
            return None

        # Build the set of columns where revenue is finite and non-zero
        rev_series = df.loc[revenue_row]
        valid_cols = [
            c for c in rev_series.index
            if rev_series[c] == rev_series[c]   # NaN guard
            and rev_series[c] != 0
        ]
        if not valid_cols:
            return None

        valid_cols = valid_cols[-_MAX_YEARS:]
        labels     = [_fy_label(c) for c in valid_cols]
        revenue    = rev_series[valid_cols].values.astype(float)

        margin_specs = [
            ("Gross Profit",     "Gross Margin",     _NAVY),
            ("Operating Income", "Operating Margin", _SLATE),
            ("Net Income",       "Net Margin",       _AMBER),
        ]

        fig, ax = _fig_and_ax()
        any_plotted = False
        for src_row, label, color in margin_specs:
            if src_row not in df.index:
                continue
            vals = df.loc[src_row, valid_cols].values.astype(float)
            pct  = (vals / revenue) * 100
            ax.plot(
                labels, pct,
                color=color, linewidth=2,
                marker="o", markersize=5,
                label=label, zorder=3,
            )
            any_plotted = True

        if not any_plotted:
            plt.close(fig)
            return None

        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_percent))
        ax.set_title(
            f"Margin Evolution ({labels[0]}–{labels[-1]})",
            fontsize=11, fontweight="bold", color="#1E293B", pad=10,
        )
        ax.tick_params(axis="both", labelsize=9, colors="#475569")
        ax.legend(fontsize=8, framealpha=0, labelcolor="#475569")
        fig.tight_layout()
        return _to_b64(fig)
    except Exception as exc:
        log.warning("Margin evolution chart failed: %s", exc)
        return None


# --- public entry point ---------------------------------------------------

def generate_charts(financials: dict, ticker: yf.Ticker) -> dict:
    """
    Public entry point.  Returns a dict with keys:
      revenue_trend    – base64 PNG string, or None
      net_income_trend – base64 PNG string, or None
      margin_evolution – base64 PNG string, or None

    Each value is ready for direct embedding:
      <img src="data:image/png;base64,{value}">

    Never raises — individual chart failures return None for that key.
    """
    symbol = financials.get("ticker", "unknown")
    log.info("Generating charts for '%s'", symbol)

    df = _load_stmt(ticker)
    if df is None:
        log.warning("No income statement data for '%s' — all charts will be None", symbol)
        return {"revenue_trend": None, "net_income_trend": None, "margin_evolution": None}

    return {
        "revenue_trend":    _revenue_trend(df),
        "net_income_trend": _net_income_trend(df),
        "margin_evolution": _margin_evolution(df),
    }
