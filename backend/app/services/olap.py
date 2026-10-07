"""OLAP-style aggregation: the user picks the dimensions to group by and the
measures to summarise; each measure is reported as average, min and max."""

from sqlalchemy import func, select

from app.db import engine, tender_outcomes as t
from app.schemas import OutcomeFilters
from app.services.outcomes import apply_filters, to_plain

# Labels come from app.i18n (dimension_label / fields.<key>).
DIMENSIONS = {
    "contracting_authority": t.c.contracting_authority,
    "location": t.c.location,
    "cpv": t.c.cpv,
    "successful_tenderer": t.c.successful_tenderer,
    "publication_year": func.year(t.c.publication_date),
    "publication_month": func.date_format(t.c.publication_date, "%Y-%m"),
    "award_year": func.year(t.c.award_date),
    "award_month": func.date_format(t.c.award_date, "%Y-%m"),
}

MEASURES = {
    "amount_awarded": t.c.amount_awarded,
    "downside_amount": t.c.downside_amount,
}

STATS = ("avg", "min", "max")
MAX_GROUPS = 10_000


class OlapError(ValueError):
    pass


def validate(group_by: list[str], measures: list[str]) -> None:
    unknown_dims = [g for g in group_by if g not in DIMENSIONS]
    if unknown_dims:
        raise OlapError(f"Unknown group_by field(s): {', '.join(unknown_dims)}")
    if len(set(group_by)) != len(group_by):
        raise OlapError("group_by fields must be unique")
    unknown_measures = [m for m in measures if m not in MEASURES]
    if unknown_measures:
        raise OlapError(f"Unknown measure(s): {', '.join(unknown_measures)}")
    if not measures:
        raise OlapError("Select at least one measure")


def _aggregates():
    return [func.count().label("count")] + [
        getattr(func, stat)(column).label(f"{key}_{stat}")
        for key, column in MEASURES.items()
        for stat in STATS
    ]


def build_query(f: OutcomeFilters, group_by: list[str]):
    dims = [DIMENSIONS[g].label(g) for g in group_by]
    stmt = apply_filters(select(*dims, *_aggregates()).select_from(t), f)
    if dims:
        stmt = stmt.group_by(*dims).order_by(*dims).limit(MAX_GROUPS)
    return stmt


def run_olap(f: OutcomeFilters, group_by: list[str], measures: list[str]) -> dict:
    validate(group_by, measures)
    keep = set(group_by) | {"count"} | {f"{m}_{s}" for m in measures for s in STATS}

    def clean(row) -> dict:
        return {k: to_plain(v) for k, v in row._mapping.items() if k in keep}

    with engine.connect() as conn:
        rows = [clean(r) for r in conn.execute(build_query(f, group_by))] if group_by else []
        totals = clean(conn.execute(build_query(f, [])).one())

    return {"group_by": group_by, "measures": measures, "rows": rows, "totals": totals}
