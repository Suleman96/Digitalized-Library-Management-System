"""Convert INTERVIEW_PREP_ACCENTURE.md to a styled PDF using fpdf2."""

from __future__ import annotations
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fpdf import FPDF

# ── Colours ───────────────────────────────────────────────────────────────────
C_ACCENT  = (43,  92, 230)   # Accenture purple-ish blue
C_H2      = (30,  58, 138)   # dark blue
C_H3      = (67, 100, 180)   # mid blue
C_MUTED   = (100, 100, 100)
C_TEXT    = (15,  23,  42)
C_BG_ALT  = (238, 242, 255)
C_BG_HEAD = (43,  92, 230)
C_WHITE   = (255, 255, 255)
C_CODE_BG = (245, 245, 245)
C_RULE    = (200, 210, 255)

PAGE_W    = 190  # usable width (A4 = 210, margins 10 each side)
LH        = 5.5  # default line height


def safe(text: str) -> str:
    """Encode to latin-1, replacing unsupported chars (emoji, etc.)."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


def strip_bold_markers(text: str) -> str:
    return text.replace("**", "")


def write_inline(pdf: FPDF, text: str, size: int = 9, lh: float = LH) -> None:
    """Write a line that may contain **bold** segments."""
    parts = text.split("**")
    bold = False
    for part in parts:
        if part:
            pdf.set_font("Helvetica", "B" if bold else "", size)
            pdf.write(lh, safe(part))
        bold = not bold


def parse_table_row(line: str) -> list[str]:
    """Split a markdown table row into cells."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


class InterviewPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*C_MUTED)
        self.cell(0, 6, safe("Accenture Interview Preparation | AI Native Product Engineer & Orchestrator"), align="C")
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*C_MUTED)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")


def build_pdf(md_path: str, out_path: str) -> None:
    with open(md_path, encoding="utf-8") as f:
        lines = f.readlines()

    pdf = InterviewPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(10, 15, 10)

    in_code   = False
    in_table  = False
    col_widths: list[float] = []
    table_header_done = False

    def end_table():
        nonlocal in_table, col_widths, table_header_done
        in_table = False
        col_widths = []
        table_header_done = False
        pdf.ln(2)

    for raw in lines:
        line = raw.rstrip("\n")

        # ── Code block toggle ──────────────────────────────────────────────
        if line.strip().startswith("```"):
            if in_table:
                end_table()
            in_code = not in_code
            if in_code:
                pdf.set_fill_color(*C_CODE_BG)
            else:
                pdf.ln(1)
            continue

        if in_code:
            pdf.set_font("Courier", "", 7.5)
            pdf.set_text_color(*C_TEXT)
            pdf.set_fill_color(*C_CODE_BG)
            pdf.multi_cell(PAGE_W, 4.5, safe(line), fill=True, align="L")
            continue

        # ── Table rows ─────────────────────────────────────────────────────
        if line.strip().startswith("|"):
            cells = parse_table_row(line)
            # Separator row (|---|---|) — treat as header end
            if all(re.match(r"^[-: ]+$", c) for c in cells if c):
                table_header_done = True
                continue

            if not in_table:
                in_table = True
                table_header_done = False
                n = len(cells)
                # Distribute widths: first col wider if it looks like a label
                if n == 2:
                    col_widths = [70.0, PAGE_W - 70.0]
                elif n == 3:
                    col_widths = [50.0, 70.0, PAGE_W - 120.0]
                elif n == 4:
                    col_widths = [40.0, 55.0, 55.0, PAGE_W - 150.0]
                elif n == 5:
                    col_widths = [30.0, 45.0, 45.0, 35.0, PAGE_W - 155.0]
                else:
                    col_widths = [PAGE_W / n] * n

            is_header = not table_header_done

            if is_header:
                pdf.set_fill_color(*C_BG_HEAD)
                pdf.set_text_color(*C_WHITE)
                pdf.set_font("Helvetica", "B", 7.5)
            else:
                pdf.set_fill_color(*C_BG_ALT if pdf.get_y() % 14 < 7 else C_WHITE)
                pdf.set_text_color(*C_TEXT)
                pdf.set_font("Helvetica", "", 7.5)

            for i, cell in enumerate(cells):
                w = col_widths[i] if i < len(col_widths) else 20.0
                pdf.cell(w, 7, safe(strip_bold_markers(cell)), border=1, fill=True)
            pdf.ln()
            continue

        # If we were in a table and hit a non-table line, close it
        if in_table:
            end_table()

        stripped = line.strip()

        # ── Horizontal rule ────────────────────────────────────────────────
        if stripped in ("---", "***", "___"):
            pdf.ln(2)
            pdf.set_draw_color(*C_RULE)
            pdf.set_line_width(0.4)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(3)
            continue

        # ── Empty line ─────────────────────────────────────────────────────
        if not stripped:
            pdf.ln(2)
            continue

        # ── H1 ────────────────────────────────────────────────────────────
        if stripped.startswith("# ") and not stripped.startswith("## "):
            text = stripped[2:].strip()
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(*C_ACCENT)
            pdf.ln(3)
            pdf.multi_cell(PAGE_W, 10, safe(text), align="C")
            pdf.set_draw_color(*C_ACCENT)
            pdf.set_line_width(0.8)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(4)
            continue

        # ── H2 ────────────────────────────────────────────────────────────
        if stripped.startswith("## ") and not stripped.startswith("### "):
            text = stripped[3:].strip()
            pdf.ln(3)
            pdf.set_fill_color(*C_ACCENT)
            pdf.set_text_color(*C_WHITE)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(PAGE_W, 8, safe("  " + text), fill=True, ln=1)
            pdf.ln(2)
            continue

        # ── H3 ────────────────────────────────────────────────────────────
        if stripped.startswith("### "):
            text = stripped[4:].strip()
            pdf.ln(2)
            pdf.set_text_color(*C_H3)
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(PAGE_W, 6, safe(text))
            pdf.set_draw_color(*C_H3)
            pdf.set_line_width(0.25)
            pdf.line(10, pdf.get_y(), 80, pdf.get_y())
            pdf.ln(2)
            continue

        # ── H4 (####) ─────────────────────────────────────────────────────
        if stripped.startswith("#### "):
            text = stripped[5:].strip()
            pdf.ln(1)
            pdf.set_text_color(*C_H2)
            pdf.set_font("Helvetica", "B", 9)
            pdf.multi_cell(PAGE_W, LH, safe(text))
            pdf.ln(1)
            continue

        # ── Blockquote ─────────────────────────────────────────────────────
        if stripped.startswith("> "):
            text = stripped[2:].strip()
            pdf.set_text_color(*C_MUTED)
            pdf.set_font("Helvetica", "I", 8.5)
            pdf.set_x(15)
            pdf.multi_cell(PAGE_W - 5, LH, safe(strip_bold_markers(text)))
            pdf.ln(1)
            continue

        # ── Bullet list ────────────────────────────────────────────────────
        if stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:].strip()
            indent = (len(line) - len(line.lstrip())) // 2
            x_offset = 12 + indent * 4
            bullet_x  = x_offset - 3
            pdf.set_x(x_offset)
            pdf.set_text_color(*C_TEXT)
            # bullet dot
            pdf.set_font("Helvetica", "", 9)
            cur_y = pdf.get_y()
            pdf.set_xy(bullet_x, cur_y)
            pdf.cell(3, LH, safe("-"))
            pdf.set_xy(x_offset, cur_y)
            write_inline(pdf, text, size=8.5, lh=LH)
            pdf.ln(LH)
            continue

        # ── Checkbox list ──────────────────────────────────────────────────
        if stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
            checked = "x" in stripped[2:5].lower()
            text = stripped[5:].strip()
            pdf.set_text_color(*C_TEXT)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_x(14)
            box = "[x]" if checked else "[ ]"
            pdf.cell(8, LH, safe(box))
            write_inline(pdf, text, size=8.5, lh=LH)
            pdf.ln(LH)
            continue

        # ── Numbered list ──────────────────────────────────────────────────
        m = re.match(r"^(\d+)\.\s+(.*)", stripped)
        if m:
            num, text = m.group(1), m.group(2)
            pdf.set_text_color(*C_TEXT)
            pdf.set_x(12)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.cell(6, LH, safe(num + "."))
            pdf.set_x(18)
            write_inline(pdf, text, size=8.5, lh=LH)
            pdf.ln(LH)
            continue

        # ── Regular paragraph ──────────────────────────────────────────────
        pdf.set_text_color(*C_TEXT)
        pdf.set_x(10)
        write_inline(pdf, stripped, size=9, lh=LH)
        pdf.ln(LH)

    pdf.output(out_path)
    print(f"PDF saved: {out_path}")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md   = os.path.join(base, "INTERVIEW_PREP_ACCENTURE.md")
    out  = os.path.join(base, "INTERVIEW_PREP_ACCENTURE.pdf")
    build_pdf(md, out)
