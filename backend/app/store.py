"""The app's own database: saved analyses and budgets. BitVision's MySQL stays read-only.

- STORE_URL (or POSTGRES_URL, set by Vercel's Postgres integration) set: Postgres.
  Needed on Vercel, where /tmp is not shared between instances and is wiped on cold starts.
- Otherwise: a local SQLite file at SAVED_VIEWS_PATH (development).

Tables are created on startup by the modules that define them.
"""

from pathlib import Path

from sqlalchemy import create_engine

from app.config import settings


def _url() -> str:
    url = settings.store_url
    if url:
        # Vercel/Neon give postgres:// or postgresql://; SQLAlchemy needs the driver name.
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url
    path = Path(settings.saved_views_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


# pool_pre_ping: serverless instances can be frozen for a while, so check a connection before using it.
engine = create_engine(_url(), pool_pre_ping=True)
