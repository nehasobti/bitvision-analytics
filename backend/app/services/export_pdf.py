from datetime import date, datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas import FIELD_LABELS
from app.services.olap import DIMENSIONS, MEASURES, STATS

# Pure-Python PDF rendering (no system libraries), so it also runs on Vercel.

BLUE = colors.HexColor("#1F4E79")
STRIPE = colors.HexColor("#f5f8fb")
TOTAL_BG = colors.HexColor("#e8eef5")
RULE = colors.HexColor("#dddddd")
MARGIN_X, MARGIN_Y = 12 * mm, 14 * mm

TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=BLUE, spaceAfter=2 * mm)
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=BLUE,
                    spaceBefore=6 * mm, spaceAfter=2 * mm)
META = ParagraphStyle("meta", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#555555"),
                      spaceAfter=3 * mm)
CELL = ParagraphStyle("cell", fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#1a1a1a"))
CELL_NUM = ParagraphStyle("cell_num", parent=CELL, alignment=2)
HEAD = ParagraphStyle("head", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
HEAD_NUM = ParagraphStyle("head_num", parent=HEAD, alignment=2)


def _money(value) -> str:
    if value is None:
        return ""
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _percent(value) -> str:
    return "" if value is None else f"{value:.3f}%".replace(".", ",")


def _date(value) -> str:
    return value.strftime("%d/%m/%Y") if isinstance(value, date) else (value or "")


def _p(text, style=CELL) -> Paragraph:
    return Paragraph(escape(str(text)), style)


def _table(header: list[Paragraph], rows: list[list], total_row: bool = False, col_widths=None) -> Table:
    table = LongTable([header] + rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, STRIPE]),
    ]
    if total_row:
        style += [
            ("BACKGROUND", (0, -1), (-1, -1), TOTAL_BG),
            ("LINEABOVE", (0, -1), (-1, -1), 1, BLUE),
        ]
    table.setStyle(TableStyle(style))
    return table


def _measure_cell(key: str, value) -> Paragraph:
    return _p(_money(value) if key == "amount_awarded" else _percent(value), CELL_NUM)


def _olap_table(olap: dict) -> Table:
    group_by = [(g, DIMENSIONS[g][0]) for g in olap["group_by"]]
    measures = [(m, MEASURES[m][0]) for m in olap["measures"]]

    header = [_p(label, HEAD) for _, label in group_by] or [_p("", HEAD)]
    header += [_p("Count", HEAD_NUM)]
    header += [_p(f"{label} {s}", HEAD_NUM) for _, label in measures for s in STATS]

    def stat_cells(row: dict) -> list:
        return [_measure_cell(key, row.get(f"{key}_{s}")) for key, _ in measures for s in STATS]

    rows = []
    for row in olap["rows"]:
        dims = [_p(row[key] if row.get(key) is not None else "—") for key, _ in group_by] or [_p("")]
        rows.append(dims + [_p(row["count"], CELL_NUM)] + stat_cells(row))

    bold = ParagraphStyle("total", parent=CELL, fontName="Helvetica-Bold")
    totals = olap["totals"]
    label_cells = [Paragraph("Total", bold)] + [""] * (max(len(group_by), 1) - 1)
    rows.append(label_cells + [_p(totals["count"], CELL_NUM)] + stat_cells(totals))

    table = _table(header, rows, total_row=True)
    if len(group_by) > 1:
        table.setStyle(TableStyle([("SPAN", (0, -1), (len(group_by) - 1, -1))]))
    return table


def _data_table(data: list[dict]) -> Table:
    numeric = ("amount_awarded", "downside_amount")
    header = [_p(label, HEAD_NUM if key in numeric else HEAD) for key, label in FIELD_LABELS.items()]
    rows = [
        [
            _p(row.get("successful_tenderer") or ""),
            _p(row.get("contracting_authority") or ""),
            _p(row.get("location") or ""),
            _p(_money(row.get("amount_awarded")), CELL_NUM),
            _p(_percent(row.get("downside_amount")), CELL_NUM),
            _p(_date(row.get("publication_date"))),
            _p(_date(row.get("award_date"))),
            _p(row.get("cpv") or ""),
        ]
        for row in data
    ]
    width = landscape(A4)[0] - 2 * MARGIN_X
    # Relative column widths: text columns get more room than numbers and dates.
    weights = [18, 18, 12, 12, 8, 9, 9, 14]
    return _table(header, rows, col_widths=[width * w / sum(weights) for w in weights])


def _page_number(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    page_w, _ = landscape(A4)
    canvas.drawRightString(page_w - MARGIN_X, MARGIN_Y / 2, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(data: list[dict], olap: dict, filters: dict) -> bytes:
    story = [
        Paragraph("Tender outcomes report", TITLE),
        Paragraph(f"Generated {datetime.now():%d/%m/%Y %H:%M} · {len(data)} records", META),
    ]

    if filters:
        bold = ParagraphStyle("filter_key", parent=CELL, fontName="Helvetica-Bold")
        filter_rows = [
            [Paragraph(escape(k.replace("_", " ").capitalize()), bold), _p(_date(v) if isinstance(v, date) else v)]
            for k, v in filters.items()
        ]
        filter_table = Table(filter_rows, hAlign="LEFT")
        filter_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        story.append(filter_table)

    group_labels = ", ".join(DIMENSIONS[g][0] for g in olap["group_by"])
    story += [
        Paragraph("Analysis" + (f" by {escape(group_labels)}" if group_labels else ""), H2),
        _olap_table(olap),
        Spacer(1, 2 * mm),
        Paragraph("Data", H2),
        _data_table(data),
    ]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_Y,
        bottomMargin=MARGIN_Y,
        title="Tender outcomes report",
    )
    doc.build(story, onFirstPage=_page_number, onLaterPages=_page_number)
    return buffer.getvalue()
