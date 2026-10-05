from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas import FIELD_LABELS
from app.services.olap import DIMENSIONS, MEASURES, STATS

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


TEMPLATES.filters.update(money=_money, percent=_percent, it_date=_date)


def build_pdf(data: list[dict], olap: dict, filters: dict) -> bytes:
    # Imported here so the API still starts if WeasyPrint's system libraries are missing.
    from weasyprint import HTML

    html = TEMPLATES.get_template("report.html").render(
        generated=datetime.now().strftime("%d/%m/%Y %H:%M"),
        filters={k.replace("_", " ").capitalize(): _date(v) if isinstance(v, date) else v for k, v in filters.items()},
        data=data,
        labels=FIELD_LABELS,
        group_by=[(g, DIMENSIONS[g][0]) for g in olap["group_by"]],
        measures=[(m, MEASURES[m][0]) for m in olap["measures"]],
        stats=STATS,
        olap_rows=olap["rows"],
        totals=olap["totals"],
    )
    return HTML(string=html).write_pdf()
