"""Insert random sample rows into tender_outcomes, for local testing only.

The app itself connects read-only, so this script uses its own connection:

    SEED_DATABASE_URL=mysql+pymysql://root:PASSWORD@127.0.0.1:3306/bitvision_development \
        python scripts/seed_sample_data.py --rows 500
"""

import argparse
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, text

AUTHORITIES = [
    "Comune di Salerno", "Comune di Napoli", "Comune di Roma", "Comune di Milano",
    "Regione Campania", "Regione Lazio", "ASL Salerno", "ASL Napoli 1 Centro",
    "Università degli Studi di Salerno", "Ministero della Difesa", "ANAS S.p.A.",
    "Provincia di Avellino",
]
LOCATIONS = ["Salerno", "Napoli", "Roma", "Milano", "Avellino", "Caserta", "Benevento", "Torino"]
TENDERERS = [
    "Wonderlab S.r.l.", "Edilsud S.p.A.", "Costruzioni Rossi S.r.l.", "InfoTech Italia S.r.l.",
    "Servizi Integrati S.p.A.", "Medical Supply S.r.l.", "Strade & Ponti S.r.l.",
    "GreenEnergy S.r.l.", "Consorzio Stabile Alfa",
]
CPVS = [
    "45000000-7", "45233140-2", "45453000-7", "72000000-5", "72212000-4",
    "79410000-1", "33100000-1", "90910000-9", "50700000-2", "09310000-5",
]


def sample_row() -> dict:
    publication = date(2022, 1, 1) + timedelta(days=random.randint(0, 1400))
    award = publication + timedelta(days=random.randint(30, 240))
    now = datetime.now()
    return {
        "successful_tenderer": random.choice(TENDERERS),
        "contracting_authority": random.choice(AUTHORITIES),
        "location": random.choice(LOCATIONS),
        "amount_awarded": Decimal(random.randint(20_000, 5_000_000)) + Decimal(random.randint(0, 99)) / 100,
        "downside_amount": Decimal(random.randint(500, 35_000)) / 1000,
        "publication_date": publication,
        "award_date": award,
        "cpv": random.choice(CPVS),
        "created_at": now,
        "updated_at": now,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=int, default=500)
    args = parser.parse_args()

    url = os.environ.get("SEED_DATABASE_URL")
    if not url:
        raise SystemExit("Set SEED_DATABASE_URL to a MySQL user with write access.")

    rows = [sample_row() for _ in range(args.rows)]
    insert = text(
        "INSERT INTO tender_outcomes (successful_tenderer, contracting_authority, location, "
        "amount_awarded, downside_amount, publication_date, award_date, cpv, created_at, updated_at) "
        "VALUES (:successful_tenderer, :contracting_authority, :location, :amount_awarded, "
        ":downside_amount, :publication_date, :award_date, :cpv, :created_at, :updated_at)"
    )
    with create_engine(url).begin() as conn:
        conn.execute(insert, rows)
    print(f"Inserted {len(rows)} sample rows into tender_outcomes")


if __name__ == "__main__":
    main()
