"""Saved analyses (filters + group by + measures, with a description).

Stored in a small SQLite file owned by this app, so the BitVision database
stays read-only. Set SAVED_VIEWS_PATH to change where the file lives.

On Vercel the code folder is read-only, so a relative path is placed in /tmp
instead. /tmp is not permanent there: saved analyses can disappear when Vercel
starts a new instance.
"""

import json
import os
from datetime import datetime
from functools import cache
from pathlib import Path

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, delete, insert, select

from app.config import settings

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


@cache
def _engine():
    """Created on first use, so a storage problem only affects saved analyses, not the whole API."""
    path = Path(settings.saved_views_path)
    if os.environ.get("VERCEL") and not path.is_absolute():
        path = Path("/tmp") / path.name
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")
    metadata.create_all(engine)
    return engine


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
    with _engine().connect() as conn:
        rows = conn.execute(select(saved_views).order_by(saved_views.c.description))
        return [_to_dict(r) for r in rows]


def create_view(description: str, filters: dict, group_by: list[str], measures: list[str]) -> dict:
    with _engine().begin() as conn:
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
    with _engine().begin() as conn:
        return conn.execute(delete(saved_views).where(saved_views.c.id == view_id)).rowcount > 0
