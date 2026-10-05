from decimal import Decimal

from sqlalchemy import Select, func, select

from app.db import engine, tender_outcomes as t
from app.schemas import OutcomeFilters

DATA_COLUMNS = [
    "id",
    "successful_tenderer",
    "contracting_authority",
    "location",
    "amount_awarded",
    "downside_amount",
    "publication_date",
    "award_date",
    "cpv",
]

SORTABLE = set(DATA_COLUMNS)


def apply_filters(stmt: Select, f: OutcomeFilters) -> Select:
    conditions = []

    if f.successful_tenderer:
        conditions.append(t.c.successful_tenderer.contains(f.successful_tenderer, autoescape=True))
    if f.contracting_authority:
        conditions.append(t.c.contracting_authority.contains(f.contracting_authority, autoescape=True))
    if f.location:
        conditions.append(t.c.location.contains(f.location, autoescape=True))
    if f.cpv:
        # CPV codes are hierarchical: "4521" matches every code under that division.
        conditions.append(t.c.cpv.startswith(f.cpv, autoescape=True))

    if f.amount_awarded_min is not None:
        conditions.append(t.c.amount_awarded >= f.amount_awarded_min)
    if f.amount_awarded_max is not None:
        conditions.append(t.c.amount_awarded <= f.amount_awarded_max)
    if f.downside_min is not None:
        conditions.append(t.c.downside_amount >= f.downside_min)
    if f.downside_max is not None:
        conditions.append(t.c.downside_amount <= f.downside_max)

    if f.publication_date_from:
        conditions.append(t.c.publication_date >= f.publication_date_from)
    if f.publication_date_to:
        conditions.append(t.c.publication_date <= f.publication_date_to)
    if f.award_date_from:
        conditions.append(t.c.award_date >= f.award_date_from)
    if f.award_date_to:
        conditions.append(t.c.award_date <= f.award_date_to)

    return stmt.where(*conditions) if conditions else stmt


def to_plain(value):
    return float(value) if isinstance(value, Decimal) else value


def list_outcomes(
    f: OutcomeFilters,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "award_date",
    sort_dir: str = "desc",
) -> tuple[int, list[dict]]:
    sort_col = t.c[sort_by if sort_by in SORTABLE else "award_date"]
    order = sort_col.asc() if sort_dir == "asc" else sort_col.desc()

    count_stmt = apply_filters(select(func.count()).select_from(t), f)
    rows_stmt = (
        apply_filters(select(*[t.c[c] for c in DATA_COLUMNS]), f)
        .order_by(order, t.c.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )

    with engine.connect() as conn:
        total = conn.execute(count_stmt).scalar_one()
        rows = [
            {k: to_plain(v) for k, v in row._mapping.items()}
            for row in conn.execute(rows_stmt)
        ]
    return total, rows


def all_outcomes(f: OutcomeFilters, limit: int) -> list[dict]:
    stmt = (
        apply_filters(select(*[t.c[c] for c in DATA_COLUMNS]), f)
        .order_by(t.c.award_date.desc(), t.c.id.desc())
        .limit(limit)
    )
    with engine.connect() as conn:
        return [{k: to_plain(v) for k, v in row._mapping.items()} for row in conn.execute(stmt)]
