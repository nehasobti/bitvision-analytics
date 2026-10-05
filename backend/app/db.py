from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    MetaData,
    Numeric,
    String,
    Table,
    create_engine,
    event,
)

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=3600)


@event.listens_for(engine, "connect")
def _force_read_only(dbapi_connection, _record):
    # This application only reads BitVision data: block any write at session level.
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET SESSION TRANSACTION READ ONLY")


metadata = MetaData()

# Mirrors the table created by BitVision's CreateTenderOutcomes migration.
tender_outcomes = Table(
    "tender_outcomes",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("successful_tenderer", String(255)),
    Column("contracting_authority", String(255)),
    Column("location", String(255)),
    Column("amount_awarded", Numeric(15, 2)),
    Column("downside_amount", Numeric(6, 3)),
    Column("publication_date", Date),
    Column("award_date", Date),
    Column("cpv", String(255)),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)
