from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.schemas import FIELD_LABELS
from app.services.olap import DIMENSIONS, MEASURES, STATS

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
TOTAL_FONT = Font(bold=True)

MONEY = '#,##0.00 "€"'
PERCENT = '0.000"%"'
DATE = "dd/mm/yyyy"


def _write_table(ws, headers: list[str], rows: list[list], formats: list[str | None]) -> None:
    ws.append(headers)
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)

    for row in rows:
        ws.append(row)

    for col_idx, fmt in enumerate(formats, start=1):
        if fmt:
            for (cell,) in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                cell.number_format = fmt

    for col_idx, header in enumerate(headers, start=1):
        width = max([len(str(header))] + [len(str(r[col_idx - 1] or "")) for r in rows[:500]])
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max(width + 2, 10), 60)

    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = ws.dimensions


def _measure_format(measure: str) -> str:
    return MONEY if measure == "amount_awarded" else PERCENT


def build_excel(data: list[dict], olap: dict, filters: dict) -> bytes:
    wb = Workbook()

    # Sheet 1: filtered data
    ws = wb.active
    ws.title = "Data"
    columns = list(FIELD_LABELS)
    formats = {
        "amount_awarded": MONEY,
        "downside_amount": PERCENT,
        "publication_date": DATE,
        "award_date": DATE,
    }
    _write_table(
        ws,
        [FIELD_LABELS[c] for c in columns],
        [[row.get(c) for c in columns] for row in data],
        [formats.get(c) for c in columns],
    )

    # Sheet 2: OLAP analysis
    ws = wb.create_sheet("Analysis")
    group_by, measures = olap["group_by"], olap["measures"]
    stat_keys = [f"{m}_{s}" for m in measures for s in STATS]
    headers = (
        [DIMENSIONS[g][0] for g in group_by]
        + ["Count"]
        + [f"{MEASURES[m][0]} – {s}" for m in measures for s in STATS]
    )
    rows = [[r.get(g) for g in group_by] + [r["count"]] + [r.get(k) for k in stat_keys] for r in olap["rows"]]
    totals = olap["totals"]
    rows.append(["TOTAL"] * max(len(group_by), 1) + [totals["count"]] + [totals.get(k) for k in stat_keys])
    if not group_by:
        headers = [""] + headers
    fmts = [None] * max(len(group_by), 1) + ["0"] + [_measure_format(m) for m in measures for _ in STATS]
    _write_table(ws, headers, rows, fmts)
    for cell in ws[ws.max_row]:
        cell.font = TOTAL_FONT

    # Sheet 3: what was exported
    ws = wb.create_sheet("Filters")
    ws.append(["Generated", datetime.now().strftime("%d/%m/%Y %H:%M")])
    ws.append(["Rows exported", len(data)])
    ws.append(["Grouped by", ", ".join(DIMENSIONS[g][0] for g in group_by) or "—"])
    for key, value in filters.items():
        ws.append([key.replace("_", " ").capitalize(), value.strftime("%d/%m/%Y") if isinstance(value, date) else value])
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 40

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
