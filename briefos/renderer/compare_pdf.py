"""
Renders a multi-ticker comparison brief as a PDF using fpdf2.
Consumes the comparison dict from processor.compare.
"""
import unicodedata
from datetime import datetime
from pathlib import Path
from fpdf import FPDF
from briefos.config import OUTPUT_DIR, PDF_MARGIN_MM, PDF_ACCENT_HEX

# Reuse colour helpers from pdf.py
def _hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

NAVY  = _hex(PDF_ACCENT_HEX)
WHITE = (255, 255, 255)
LIGHT = (245, 247, 250)
DARK  = (30,  30,  40)
MED   = (100, 110, 125)

_UNICODE_MAP = {
    "—": "--", "–": "-",
    "‘": "'",  "’": "'",
    "“": '"',  "”": '"',
    "…": "...",
    "·": ".",  "•": "*",
    "®": "(R)", "™": "(TM)",
}

def _t(text: str) -> str:
    for char, repl in _UNICODE_MAP.items():
        text = text.replace(char, repl)
    text = unicodedata.normalize("NFKD", text)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class ComparePDF(FPDF):
    def __init__(self, tickers: list[str]):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.tickers_label = "  vs  ".join(tickers)
        self.set_margins(PDF_MARGIN_MM, PDF_MARGIN_MM, PDF_MARGIN_MM)
        self.set_auto_page_break(auto=True, margin=PDF_MARGIN_MM + 8)

    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 297, 18, "F")
        self.set_y(4)
        self.set_x(PDF_MARGIN_MM)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*WHITE)
        self.cell(0, 10, _t(f"BriefOS  |  Comparison  |  {self.tickers_label}"), ln=False, align="L")
        self.set_font("Helvetica", "", 8)
        self.set_x(-PDF_MARGIN_MM - 40)
        self.cell(40, 10, "PEER COMPARISON", align="R")
        self.set_text_color(*DARK)
        self.ln(14)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*MED)
        self.cell(0, 6, _t(f"BriefOS -- Generated {datetime.now().strftime('%Y-%m-%d')}  |  Page {self.page_no()}"), align="C")
        self.set_text_color(*DARK)


def _section_heading(pdf: ComparePDF, title: str):
    pdf.set_fill_color(*NAVY)
    pdf.rect(PDF_MARGIN_MM, pdf.get_y(), 3, 6, "F")
    pdf.set_x(PDF_MARGIN_MM + 5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6, _t(title.upper()), ln=True)
    pdf.set_text_color(*DARK)
    pdf.ln(1)


def render_comparison(comparison: dict) -> Path:
    """
    Build and save the comparison PDF. Returns the output file Path.
    Uses landscape A4 to accommodate multiple ticker columns.
    """
    tickers  = comparison["tickers"]
    names    = comparison["names"]
    sections = comparison["sections"]
    n        = len(tickers)

    ts       = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    label    = "_vs_".join(tickers)
    filename = OUTPUT_DIR / f"COMPARE_{label}_{ts}.pdf"

    pdf = ComparePDF(tickers=tickers)
    pdf.add_page()

    # Page width in landscape A4 = 297mm
    page_w   = 297 - 2 * PDF_MARGIN_MM
    label_w  = page_w * 0.28
    val_w    = (page_w - label_w) / n
    row_h    = 6.5

    # -- Cover block
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 9, "Peer Comparison Brief", ln=True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MED)
    pdf.cell(0, 5, _t(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}  |  Data: yfinance (Yahoo Finance)"), ln=True)
    pdf.ln(4)

    # -- Company name header row
    pdf.set_fill_color(*NAVY)
    pdf.rect(PDF_MARGIN_MM, pdf.get_y(), page_w, row_h + 1, "F")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*WHITE)
    pdf.set_x(PDF_MARGIN_MM)
    pdf.cell(label_w, row_h, "  Metric", border=0)
    for name in names:
        # Truncate long names to fit column
        short = name if len(name) <= 22 else name[:20] + ".."
        pdf.cell(val_w, row_h, _t(f"  {short}"), border=0)
    pdf.ln(row_h + 1)
    pdf.set_text_color(*DARK)

    # -- Ticker subheader row
    pdf.set_fill_color(*LIGHT)
    pdf.rect(PDF_MARGIN_MM, pdf.get_y(), page_w, row_h, "F")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*MED)
    pdf.set_x(PDF_MARGIN_MM)
    pdf.cell(label_w, row_h, "", border=0)
    for ticker in tickers:
        pdf.cell(val_w, row_h, _t(f"  {ticker}"), border=0)
    pdf.ln(row_h)
    pdf.set_text_color(*DARK)
    pdf.ln(3)

    # -- Sections and rows
    for section in sections:
        _section_heading(pdf, section["title"])
        for idx, row_data in enumerate(section["rows"]):
            shade = idx % 2 == 0
            if shade:
                pdf.set_fill_color(*LIGHT)
                pdf.rect(PDF_MARGIN_MM, pdf.get_y(), page_w, row_h, "F")

            pdf.set_x(PDF_MARGIN_MM)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*MED)
            pdf.cell(label_w, row_h, _t(f"  {row_data['label']}"), border=0)

            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*DARK)
            for val in row_data["values"]:
                pdf.cell(val_w, row_h, _t(f"  {val}"), border=0)
            pdf.ln(row_h)
        pdf.ln(2)

    # -- Sources footer
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*MED)
    pdf.cell(0, 5, _t("Sources: yfinance (Yahoo Finance). Data is indicative only -- always verify against primary filings."), ln=True)

    pdf.output(str(filename))
    return filename
