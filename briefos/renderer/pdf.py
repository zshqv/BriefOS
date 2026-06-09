"""
Renders a BriefOS research brief as a PDF using fpdf2.
Consumes the sections dict from processor.content and flags from processor.flags.
"""
import textwrap
import unicodedata
from datetime import datetime
from pathlib import Path
from fpdf import FPDF
from briefos.config import OUTPUT_DIR, PDF_MARGIN_MM, PDF_ACCENT_HEX


_UNICODE_MAP = {
    "—": "--", "–": "-",    # em/en dash
    "‘": "'",  "’": "'",    # curly single quotes
    "“": '"',  "”": '"',    # curly double quotes
    "…": "...",                  # ellipsis
    "·": ".",  "•": "*",   # middle dot / bullet
    "®": "(R)", "™": "(TM)",
}

def _t(text: str) -> str:
    """Sanitize text to Latin-1 safe string for fpdf2 Helvetica rendering."""
    for char, repl in _UNICODE_MAP.items():
        text = text.replace(char, repl)
    # Final pass: strip any remaining non-latin-1 via NFKD decomposition
    text = unicodedata.normalize("NFKD", text)
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ── Colour palette ────────────────────────────────────────────────────────────
def _hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

NAVY   = _hex(PDF_ACCENT_HEX)   # headers, accents
WHITE  = (255, 255, 255)
LIGHT  = (245, 247, 250)        # alternating row background
DARK   = (30,  30,  40)         # body text
MED    = (100, 110, 125)        # subtext
GREEN  = (39,  174, 96)
AMBER  = (230, 126, 34)
RED    = (192, 57,  43)

SEV_COLOUR = {"positive": GREEN, "caution": AMBER, "alert": RED}
SEV_ICON   = {"positive": "+", "caution": "!", "alert": "X"}


class BriefPDF(FPDF):
    def __init__(self, ticker: str, company: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.ticker  = ticker
        self.company = company
        self.set_margins(PDF_MARGIN_MM, PDF_MARGIN_MM, PDF_MARGIN_MM)
        self.set_auto_page_break(auto=True, margin=PDF_MARGIN_MM + 8)

    # ── Page chrome ───────────────────────────────────────────────────────────
    def header(self):
        # Navy banner
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 18, "F")
        self.set_y(4)
        self.set_x(PDF_MARGIN_MM)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*WHITE)
        self.cell(0, 10, _t(f"BriefOS  |  {self.ticker}  |  {self.company}"), ln=False, align="L")
        self.set_font("Helvetica", "", 8)
        self.set_x(-PDF_MARGIN_MM - 30)
        self.cell(30, 10, "RESEARCH BRIEF", align="R")
        self.set_text_color(*DARK)
        self.ln(14)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*MED)
        self.cell(0, 6, _t(f"BriefOS -- Generated {datetime.now().strftime('%Y-%m-%d')}  |  Page {self.page_no()}"), align="C")
        self.set_text_color(*DARK)


# ── Helper draw functions ─────────────────────────────────────────────────────

def _section_heading(pdf: BriefPDF, title: str):
    """Navy left-bar section heading."""
    pdf.set_fill_color(*NAVY)
    pdf.rect(PDF_MARGIN_MM, pdf.get_y(), 3, 6, "F")
    pdf.set_x(PDF_MARGIN_MM + 5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6, _t(title.upper()), ln=True)
    pdf.set_text_color(*DARK)
    pdf.ln(1)


def _kv_table(pdf: BriefPDF, rows: dict, cols: int = 2):
    """Render a key-value grid with alternating row shading."""
    items  = list(rows.items())
    col_w  = (210 - 2 * PDF_MARGIN_MM) / cols
    key_w  = col_w * 0.55
    val_w  = col_w * 0.45
    row_h  = 6.5
    pair_w = cols

    for idx in range(0, len(items), pair_w):
        pair  = items[idx: idx + pair_w]
        shade = (idx // pair_w) % 2 == 0
        if shade:
            pdf.set_fill_color(*LIGHT)
            pdf.rect(PDF_MARGIN_MM, pdf.get_y(), 210 - 2 * PDF_MARGIN_MM, row_h, "F")

        x_start = pdf.get_x()
        y_start = pdf.get_y()
        for col_i, (k, v) in enumerate(pair):
            x = PDF_MARGIN_MM + col_i * col_w
            pdf.set_xy(x, y_start)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*MED)
            pdf.cell(key_w, row_h, _t(str(k)), border=0)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*DARK)
            pdf.cell(val_w, row_h, _t(str(v)), border=0)
        pdf.ln(row_h)

    pdf.ln(3)


def _paragraph(pdf: BriefPDF, text: str, size: int = 8, line_h: float = 4.5):
    """Word-wrap a block of text."""
    if not text:
        return
    avail = 210 - 2 * PDF_MARGIN_MM
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*DARK)
    # fpdf2's multi_cell handles wrapping
    pdf.multi_cell(avail, line_h, _t(text), align="L")
    pdf.ln(2)


def _flags_block(pdf: BriefPDF, flags: list):
    """Render flag chips with coloured severity indicators."""
    if not flags:
        return

    avail = 210 - 2 * PDF_MARGIN_MM
    row_h = 6.5
    col_icon  = avail * 0.22
    col_label = avail * 0.30
    col_detail = avail * 0.48

    for sev, label, detail in flags:
        colour = SEV_COLOUR.get(sev, MED)
        icon   = SEV_ICON.get(sev, "*")

        # Measure how many lines the detail text will need
        # so we can set the correct total row height before drawing
        pdf.set_font("Helvetica", "", 7.5)
        detail_clean = _t(detail)
        char_width   = pdf.get_string_width("x")
        chars_per_line = max(1, int(col_detail / (char_width * 0.72)))
        wrapped_lines  = max(1, -(-len(detail_clean) // chars_per_line))  # ceiling division
        total_h = max(row_h, wrapped_lines * row_h * 0.85)

        # Snapshot Y before drawing so all three columns start at same Y
        y = pdf.get_y()

        # Check if this row will overflow the page before drawing
        if y + total_h > pdf.h - pdf.b_margin:
            pdf.add_page()
            y = pdf.get_y()

        # Column 1 — severity chip (filled colour block)
        pdf.set_xy(PDF_MARGIN_MM, y)
        pdf.set_fill_color(*colour)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_icon, row_h, _t(f"  {icon}  {sev.upper()}"), fill=True, border=0)

        # Column 2 — flag label
        pdf.set_xy(PDF_MARGIN_MM + col_icon, y)
        pdf.set_text_color(*DARK)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_label, row_h, _t(f" {label}"), border=0)

        # Column 3 — detail text (may wrap, but Y is anchored above)
        pdf.set_xy(PDF_MARGIN_MM + col_icon + col_label, y)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*MED)
        pdf.multi_cell(col_detail, row_h * 0.85, detail_clean, align="L")

        # Advance Y to the correct next position regardless of wrap
        next_y = max(pdf.get_y(), y + row_h)
        pdf.set_y(next_y + 1)

    pdf.ln(2)


# ── Public entry point ────────────────────────────────────────────────────────

def render(sections: dict, flags: list, ticker: str) -> Path:
    """
    Build and save the PDF.  Returns the output file Path.
    """
    name     = sections["header"]["name"]
    fy       = sections["header"]["fiscal_year"]
    ts       = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = OUTPUT_DIR / f"{ticker}_{ts}.pdf"

    pdf = BriefPDF(ticker=ticker, company=name)
    pdf.add_page()

    # ── Cover block ───────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 10, _t(name), ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MED)
    subtitle = f"{ticker}  |  {sections['identity'].get('Sector', '')}  |  {sections['identity'].get('Country', '')}  |  {fy}  |  {sections['header']['timestamp']}"
    pdf.cell(0, 5, _t(subtitle), ln=True)
    pdf.ln(4)

    # ── Overview ──────────────────────────────────────────────────────────────
    _section_heading(pdf, "Business Overview")
    _paragraph(pdf, sections["overview"]["text"])
    if sections["overview"].get("wiki_extra"):
        _paragraph(pdf, sections["overview"]["wiki_extra"])

    # ── Identity ─────────────────────────────────────────────────────────────
    _section_heading(pdf, "Company Profile")
    _kv_table(pdf, sections["identity"], cols=2)

    # ── Flags ─────────────────────────────────────────────────────────────────
    if flags:
        _section_heading(pdf, "Key Flags")
        _flags_block(pdf, flags)

    # ── Valuation ─────────────────────────────────────────────────────────────
    _section_heading(pdf, "Valuation")
    _kv_table(pdf, sections["valuation"], cols=2)

    # ── Profitability ─────────────────────────────────────────────────────────
    _section_heading(pdf, "Profitability")
    _kv_table(pdf, sections["profitability"], cols=2)

    # ── Income statement ──────────────────────────────────────────────────────
    _section_heading(pdf, f"Income Statement ({fy})")
    _kv_table(pdf, sections["income"], cols=2)

    # ── Balance sheet ─────────────────────────────────────────────────────────
    _section_heading(pdf, "Balance Sheet")
    _kv_table(pdf, sections["balance"], cols=2)

    # ── Cash flow ─────────────────────────────────────────────────────────────
    _section_heading(pdf, f"Cash Flow ({fy})")
    _kv_table(pdf, sections["cashflow"], cols=2)

    # ── Market data ───────────────────────────────────────────────────────────
    _section_heading(pdf, "Market Data")
    _kv_table(pdf, sections["market"], cols=2)

    # ── Dividends ─────────────────────────────────────────────────────────────
    _section_heading(pdf, "Dividends")
    _kv_table(pdf, sections["dividends"], cols=2)

    # ── Wikipedia categories as tags ─────────────────────────────────────────
    cats = sections.get("categories", [])
    if cats:
        _section_heading(pdf, "Tags")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*MED)
        pdf.multi_cell(0, 5, _t("  |  ".join(cats)), align="L")
        pdf.ln(2)

    # ── Sources ───────────────────────────────────────────────────────────────
    pdf.ln(2)
    _section_heading(pdf, "Sources")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*MED)
    for src in sections["header"]["sources"]:
        pdf.cell(0, 5, _t(f"  * {src}"), ln=True)

    pdf.output(str(filename))
    return filename
