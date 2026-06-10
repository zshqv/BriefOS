"""
Renders a BriefOS research brief as an HTML file using Jinja2.
Consumes the sections dict from processor.content, plus flags, derived, charts, and news.
"""
import logging
from datetime import datetime
from pathlib import Path

import jinja2

from briefos.config import OUTPUT_DIR

log = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def render_brief(
    content:    dict,
    financials: dict,
    flags:      list,
    derived:    dict,
    charts:     dict,
    news:       list,
) -> Path:
    """
    Render and save a single-ticker HTML brief. Returns the output file Path.

    content    – sections dict from processor.content.build()
    financials – raw financials dict from fetcher.financials.fetch()
    flags      – list of (severity, label, detail) tuples from processor.flags
    derived    – dict from processor.content.compute_derived_metrics()
    charts     – dict of base64 PNG strings from charts.generator
    news       – list of headline dicts from fetcher.news
    """
    ticker = financials["ticker"]
    ts     = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = OUTPUT_DIR / f"{ticker}_{ts}.html"

    log.info("Rendering HTML brief for '%s'", ticker)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    template = env.get_template("brief.html")

    html = template.render(
        header        = content["header"],
        overview      = content["overview"],
        identity      = content["identity"],
        valuation     = content["valuation"],
        profitability = content["profitability"],
        income        = content["income"],
        balance       = content["balance"],
        cashflow      = content["cashflow"],
        market        = content["market"],
        dividends     = content["dividends"],
        categories    = content.get("categories", []),
        flags         = flags,
        derived       = derived,
        charts        = charts or {},
        news          = news   or [],
    )

    filename.write_text(html, encoding="utf-8")
    log.info("HTML brief written: %s", filename)
    return filename
