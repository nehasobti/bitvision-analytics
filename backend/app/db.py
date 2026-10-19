from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
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
    # Added by LinkTenderOutcomesToTenders; only the "Le mie gare" page reads it.
    Column("tender_id", BigInteger),
)

# Score list of an outcome (CreateTenderOutcomeParticipants); azienda_id marks our company's row.
tender_outcome_participants = Table(
    "tender_outcome_participants",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tender_outcome_id", BigInteger),
    Column("azienda_id", BigInteger),
    Column("participant", String(255)),
    Column("technical_score", Numeric(8, 3)),
    Column("economic_score", Numeric(8, 3)),
    Column("downside_amount", Numeric(6, 3)),
    Column("position", Integer),
)

# BitVision tables used by "Le mie gare" (only the columns read here).
tenders = Table(
    "tenders",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("contracting_authority_id", Integer),
    Column("title", String(255)),
    Column("cig", String(255)),
    Column("status", Integer),
    Column("base_amount", Numeric(15, 2)),
    Column("submission_deadline", DateTime),
    Column("execution_location", String(255)),
)

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("firstname", String(255)),
    Column("lastname", String(255)),
    Column("agency_name", String(255)),
    Column("azienda_id", BigInteger),
)

aziendas = Table(
    "aziendas",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("nome", String(255)),
)

tender_bookmarks = Table(
    "tender_bookmarks",
    metadata,
    Column("tender_id", BigInteger),
    Column("user_id", BigInteger),
    Column("active", Boolean),
)

tender_participants = Table(
    "tender_participants",
    metadata,
    Column("tender_id", BigInteger),
    Column("user_id", Integer),
)
