"""Saved analyses (filters + group by + measures, with a description).

Stored in a small SQLite file owned by this app, so the BitVision database
stays read-only. Set SAVED_VIEWS_PATH to change where the file lives.
"""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, delete, insert, select

from app.config import settings

_path = Path(settings.saved_views_path)
_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{_path}")
metadata = MetaData()

saved_views = Table(
    "saved_views",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("description", String(255), nullable=False),
    Column("filters", Text, nullable=False),
    Column("group_by", Text, nullable=False),
    Column("measures", Text, nullable=False),
    Column("created_at", DateTime, nullable=False),
)

metadata.create_all(engine)


def _to_dict(row) -> dict:
    return {
        "id": row.id,
        "description": row.description,
        "filters": json.loads(row.filters),
        "group_by": json.loads(row.group_by),
        "measures": json.loads(row.measures),
        "created_at": row.created_at,
    }


def list_views() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(select(saved_views).order_by(saved_views.c.description))
        return [_to_dict(r) for r in rows]


def create_view(description: str, filters: dict, group_by: list[str], measures: list[str]) -> dict:
    with engine.begin() as conn:
        result = conn.execute(
            insert(saved_views).values(
                description=description,
                filters=json.dumps(filters),
                group_by=json.dumps(group_by),
                measures=json.dumps(measures),
                created_at=datetime.now(),
            )
        )
        row = conn.execute(select(saved_views).where(saved_views.c.id == result.inserted_primary_key[0])).one()
    return _to_dict(row)


def delete_view(view_id: int) -> bool:
    with engine.begin() as conn:
        return conn.execute(delete(saved_views).where(saved_views.c.id == view_id)).rowcount > 0
