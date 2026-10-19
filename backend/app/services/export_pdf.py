from datetime import date, datetime
from functools import cache
from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.i18n import dimension_label, field_labels, filter_label, t
from app.services.mining_report import sections, settings_rows
from app.services.my_tenders_report import columns as my_columns, filter_rows, summary_rows
from app.services.olap import STATS

TEMPLATES = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates"),
    autoescape=select_autoescape(["html"]),
)


def _money(value) -> str:
    if value is None:
        return ""
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _percent(value) -> str:
    return "" if value is None else f"{value:.3f}%".replace(".", ",")


def _date(value) -> str:
    return value.strftime("%d/%m/%Y") if isinstance(value, date) else (value or "")


def _cell(value, kind: str) -> str:
    """Format one data mining report cell (kinds defined in mining_report)."""
    if value is None:
        return ""
    if kind == "money":
        return _money(value)
    if kind == "percent":
        return _percent(value)
    if kind == "date":
        return _date(value)
    if kind == "number":
        return f"{value:.2f}".replace(".", ",")
    if kind == "list":
        return ", ".join(value)
    if kind == "direction":
        return t(f"mining.{value}")
    if kind == "status":
        return t(f"status.{value}")
    if kind == "result":
        return t(f"my.{value}")
    if kind == "points":
        return f"{value:+.3f}".replace(".", ",")
    return str(value)


def _plain_number(value) -> str:
    """30.0 -> "30", 1.5 -> "1,5" (Italian decimal comma, no trailing zeros)."""
    if isinstance(value, float):
        return f"{value:g}".replace(".", ",")
    return str(value)


TEMPLATES.filters.update(money=_money, percent=_percent, it_date=_date, cell=_cell, plain_number=_plain_number)
TEMPLATES.globals.update(t=t)


@cache
def _weasyprint():
    """WeasyPrint's HTML class, or None when its system libraries (Pango) are missing,
    e.g. on Vercel or Windows. Imported lazily so the API starts either way."""
    try:
        from weasyprint import HTML
    except (ImportError, OSError):
        return None
    return HTML


def _render(template: str, **context) -> bytes:
    """Render a template to PDF: WeasyPrint when available, otherwise xhtml2pdf
    (pure Python, no system libraries, simpler CSS: no page footer or zebra rows)."""
    html_class = _weasyprint()
    html = TEMPLATES.get_template(template).render(simple_pdf=html_class is None, **context)
    if html_class:
        return html_class(string=html).write_pdf()

    from xhtml2pdf import pisa

    buffer = BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if result.err:
        raise RuntimeError("PDF generation failed")
    return buffer.getvalue()


def build_pdf(data: list[dict], olap: dict, filters: dict) -> bytes:
    return _render(
        "report.html",
        generated=datetime.now().strftime("%d/%m/%Y %H:%M"),
        filters={filter_label(k): _date(v) if isinstance(v, date) else v for k, v in filters.items()},
        data=data,
        labels=field_labels(),
        group_by=[(g, dimension_label(g)) for g in olap["group_by"]],
        measures=[(m, t(f"fields.{m}")) for m in olap["measures"]],
        stats=STATS,
        olap_rows=olap["rows"],
        totals=olap["totals"],
    )


def build_mining_pdf(result: dict, filters: dict) -> bytes:
    return _render(
        "mining_report.html",
        generated=datetime.now().strftime("%d/%m/%Y %H:%M"),
        records=result["records"],
        filters={filter_label(k): _date(v) if isinstance(v, date) else v for k, v in filters.items()},
        settings=settings_rows(result),
        sections=sections(result),
    )


def build_my_tenders_pdf(result: dict, filters: dict, azienda_name: str | None) -> bytes:
    return _render(
        "my_tenders_report.html",
        generated=datetime.now().strftime("%d/%m/%Y %H:%M"),
        filters=filter_rows(filters, azienda_name),
        summary=summary_rows(result["summary"]),
        columns=my_columns(),
        rows=result["rows"],
    )
