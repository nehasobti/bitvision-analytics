"""'Gestione budget': cost breakdown of a BitVision tender.

The tender's base amount (Base d'asta) is read from BitVision; everything the user
enters (Oneri sicurezza and the task rows) is stored in the app's own SQLite file,
next to the saved analyses, so the BitVision database stays read-only.

Row kinds:
- unit:        Totale = Prezzo unitario * Unità di misura    ("A unità di misura")
- lump_sum:    Totale entered by the user                    ("A cottimo")
- percentage:  Totale = Unità di misura % of the sum of the   ("Percentuale")
               selected rows' totals, recalculated on every read
"""

import json
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, Text, delete, insert, select, update

from app.saved_views import engine as store

KINDS = ("unit", "lump_sum", "percentage")

metadata = MetaData()

budgets = Table(
    "budgets",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tender_id", Integer, nullable=False, unique=True),
    Column("safety_costs", Float),  # Oneri sicurezza
    Column("updated_at", DateTime, nullable=False),
)

budget_lines = Table(
    "budget_lines",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("budget_id", Integer, nullable=False, index=True),
    Column("position", Integer, nullable=False),
    Column("kind", String(20), nullable=False),
    Column("task", String(255), nullable=False),
    Column("quantity", Float),  # Unità di misura (a percentage for kind "percentage")
    Column("unit_price", Float),  # Prezzo unitario
    Column("total", Float),  # stored for unit / lump_sum, computed for percentage
    Column("note", Text),
    Column("refs", Text),  # JSON list of line ids summed by a percentage row
)

metadata.create_all(store)


class BudgetLineIn(BaseModel):
    kind: Literal["unit", "lump_sum", "percentage"]
    task: str = Field(min_length=1, max_length=255)
    quantity: float | None = Field(None, ge=0)
    unit_price: float | None = Field(None, ge=0)
    total: float | None = None
    note: str | None = None
    refs: list[int] = []

    @model_validator(mode="after")
    def _required_fields(self):
        if self.kind == "unit" and (self.quantity is None or self.unit_price is None):
            raise ValueError("'Unità di misura' and 'Prezzo unitario' are required")
        if self.kind == "lump_sum" and self.total is None:
            raise ValueError("'Totale' is required")
        if self.kind == "percentage" and (self.quantity is None or not self.refs):
            raise ValueError("A percentage and at least one task are required")
        return self


class BudgetError(ValueError):
    pass


def _dec(value) -> Decimal:
    return Decimal(str(value or 0))


def compute_totals(lines: list[dict]) -> dict[int, float | None]:
    """Total of every line; percentage lines sum the totals of their referenced lines
    (which may be percentage lines too). Cycles or missing references give None.
    Exact decimal maths, rounded half-up to 4 decimals like Excel."""
    by_id = {line["id"]: line for line in lines}
    exact: dict[int, Decimal | None] = {}
    visiting: set[int] = set()

    def total_of(line_id: int) -> Decimal | None:
        if line_id in exact:
            return exact[line_id]
        line = by_id.get(line_id)
        if line is None or line_id in visiting:
            return None
        if line["kind"] == "unit":
            value = _dec(line["quantity"]) * _dec(line["unit_price"])
        elif line["kind"] == "lump_sum":
            value = None if line["total"] is None else _dec(line["total"])
        else:
            visiting.add(line_id)
            parts = [total_of(ref) for ref in line["refs"]]
            visiting.discard(line_id)
            value = None if any(p is None for p in parts) else sum(parts, Decimal(0)) * _dec(line["quantity"]) / 100
        exact[line_id] = value
        return value

    for line in lines:
        total_of(line["id"])
    return {
        line_id: None if value is None else float(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
        for line_id, value in exact.items()
        if line_id in by_id
    }


def _line_dict(row) -> dict:
    data = dict(row._mapping)
    data["refs"] = json.loads(data["refs"] or "[]")
    return data


def _budget_id(conn, tender_id: int, create: bool) -> int | None:
    row = conn.execute(select(budgets.c.id).where(budgets.c.tender_id == tender_id)).first()
    if row:
        return row.id
    if not create:
        return None
    return conn.execute(insert(budgets).values(tender_id=tender_id, updated_at=datetime.now())).inserted_primary_key[0]


def _lines(conn, budget_id: int | None) -> list[dict]:
    if budget_id is None:
        return []
    rows = conn.execute(select(budget_lines).where(budget_lines.c.budget_id == budget_id).order_by(budget_lines.c.position))
    return [_line_dict(r) for r in rows]


def get_budget(tender_id: int) -> dict:
    with store.connect() as conn:
        row = conn.execute(select(budgets).where(budgets.c.tender_id == tender_id)).first()
        lines = _lines(conn, row.id if row else None)
    totals = compute_totals(lines)
    for line in lines:
        line["total"] = totals[line["id"]]
    return {
        "safety_costs": row.safety_costs if row else None,
        "lines": lines,
        "lines_total": round(sum(t for t in totals.values() if t is not None), 4),
    }


def set_safety_costs(tender_id: int, value: float | None) -> None:
    with store.begin() as conn:
        budget_id = _budget_id(conn, tender_id, create=True)
        conn.execute(update(budgets).where(budgets.c.id == budget_id).values(safety_costs=value, updated_at=datetime.now()))


def _values(line: BudgetLineIn, existing_ids: set[int], line_id: int | None = None) -> dict:
    refs = []
    if line.kind == "percentage":
        refs = list(dict.fromkeys(line.refs))  # keep order, drop duplicates
        if line_id in refs or not set(refs) <= existing_ids:
            raise BudgetError("Selected tasks must be other rows of this budget")
    return {
        "kind": line.kind,
        "task": line.task.strip(),
        "quantity": line.quantity if line.kind != "lump_sum" else None,
        "unit_price": line.unit_price if line.kind == "unit" else None,
        "total": line.total if line.kind == "lump_sum" else None,
        "note": (line.note or "").strip() or None,
        "refs": json.dumps(refs),
    }


def add_line(tender_id: int, line: BudgetLineIn) -> None:
    with store.begin() as conn:
        budget_id = _budget_id(conn, tender_id, create=True)
        lines = _lines(conn, budget_id)
        values = _values(line, {l["id"] for l in lines})
        position = max((l["position"] for l in lines), default=0) + 1
        conn.execute(insert(budget_lines).values(budget_id=budget_id, position=position, **values))


def update_line(tender_id: int, line_id: int, line: BudgetLineIn) -> None:
    with store.begin() as conn:
        budget_id = _budget_id(conn, tender_id, create=False)
        lines = _lines(conn, budget_id)
        if line_id not in {l["id"] for l in lines}:
            raise LookupError("Row not found")
        values = _values(line, {l["id"] for l in lines}, line_id)
        conn.execute(update(budget_lines).where(budget_lines.c.id == line_id).values(**values))


def delete_line(tender_id: int, line_id: int) -> None:
    """Deletes the row and removes it from the percentage rows that summed it."""
    with store.begin() as conn:
        budget_id = _budget_id(conn, tender_id, create=False)
        lines = _lines(conn, budget_id)
        if line_id not in {l["id"] for l in lines}:
            raise LookupError("Row not found")
        conn.execute(delete(budget_lines).where(budget_lines.c.id == line_id))
        for l in lines:
            if line_id in l["refs"]:
                refs = [r for r in l["refs"] if r != line_id]
                conn.execute(update(budget_lines).where(budget_lines.c.id == l["id"]).values(refs=json.dumps(refs)))


def reorder_lines(tender_id: int, ids: list[int]) -> None:
    with store.begin() as conn:
        budget_id = _budget_id(conn, tender_id, create=False)
        current = {l["id"] for l in _lines(conn, budget_id)}
        if set(ids) != current or len(ids) != len(current):
            raise BudgetError("The new order must contain every row once")
        for position, line_id in enumerate(ids, start=1):
            conn.execute(update(budget_lines).where(budget_lines.c.id == line_id).values(position=position))
