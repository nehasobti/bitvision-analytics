"""'Le mie gare': tenders our company took part in, comparing our ribasso with the winner's.

A tender belongs to the company when one of its users saved it or took part in it
(same rule as the "Gara" select in BitVision's Archivio esiti). The outcome is linked
through tender_outcomes.tender_id; our row in the score list has azienda_id set.
"""

from datetime import date, datetime
from statistics import mean
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select

from app.db import (
    aziendas,
    engine,
    tender_bookmarks,
    tender_outcome_participants as tp,
    tender_outcomes as to,
    tender_participants,
    tenders,
    users,
)
from app.services.outcomes import to_plain

# BitVision Tender#status enum, in order (stored as integer).
STATUSES = [
    "draft", "published", "clarification_open", "bidding_open", "bidding_closed",
    "under_evaluation", "awarded", "contracted", "completed", "cancelled",
]
CONCLUDED = ["awarded", "contracted", "completed"]
RESULTS = ("won", "lost", "not_ranked", "no_outcome")


class MyTendersFilters(BaseModel):
    azienda_id: int | None = None
    q: str | None = None  # title, CIG or contracting authority
    status: list[str] = []  # tender statuses; "concluded" = awarded, contracted, completed
    result: Literal["won", "lost", "not_ranked", "no_outcome"] | None = None
    deadline_from: date | None = None
    deadline_to: date | None = None

    def active(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v not in (None, "", [])}


def list_aziende() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(select(aziendas.c.id, aziendas.c.nome).order_by(aziendas.c.nome))
        return [{"id": r.id, "name": r.nome} for r in rows]


def _status_codes(keys: list[str]) -> list[int]:
    wanted = set(CONCLUDED if "concluded" in keys else []) | {k for k in keys if k in STATUSES}
    return [STATUSES.index(k) for k in wanted]


def _tenders_query(f: MyTendersFilters):
    company_users = select(users.c.id).where(users.c.azienda_id == f.azienda_id)
    saved = select(tender_bookmarks.c.tender_id).where(
        tender_bookmarks.c.active.is_(True), tender_bookmarks.c.user_id.in_(company_users)
    )
    participated = select(tender_participants.c.tender_id).where(tender_participants.c.user_id.in_(company_users))

    authority = func.coalesce(
        func.nullif(users.c.agency_name, ""), func.concat_ws(" ", users.c.firstname, users.c.lastname)
    ).label("contracting_authority")

    stmt = (
        select(
            tenders.c.id.label("tender_id"),
            tenders.c.title,
            tenders.c.cig,
            tenders.c.status,
            tenders.c.base_amount,
            tenders.c.submission_deadline,
            authority,
            to.c.id.label("outcome_id"),
            to.c.successful_tenderer,
            to.c.downside_amount.label("outcome_downside"),
            to.c.award_date,
        )
        .select_from(
            tenders.outerjoin(users, users.c.id == tenders.c.contracting_authority_id).outerjoin(
                to, to.c.tender_id == tenders.c.id
            )
        )
        .where(or_(tenders.c.id.in_(saved), tenders.c.id.in_(participated)))
        .order_by(tenders.c.submission_deadline.desc(), tenders.c.id.desc())
    )

    if f.q:
        like = f"%{f.q}%"
        stmt = stmt.where(or_(tenders.c.title.like(like), tenders.c.cig.like(like), authority.like(like)))
    if f.status:
        stmt = stmt.where(tenders.c.status.in_(_status_codes(f.status)))
    if f.deadline_from:
        stmt = stmt.where(tenders.c.submission_deadline >= datetime.combine(f.deadline_from, datetime.min.time()))
    if f.deadline_to:
        stmt = stmt.where(tenders.c.submission_deadline <= datetime.combine(f.deadline_to, datetime.max.time()))
    return stmt


def compare(row: dict, participants: list[dict], azienda_id: int | None) -> dict:
    """Our position/ribasso vs the winner's for one tender. The winner is position 1
    of the score list; without a score list, the outcome's own winner fields are used."""
    winner = next((p for p in participants if p["position"] == 1), None)
    ours = next((p for p in participants if azienda_id is not None and p["azienda_id"] == azienda_id), None)

    winner_name = winner["participant"] if winner else row.get("successful_tenderer")
    winner_downside = winner["downside_amount"] if winner else row.get("outcome_downside")
    our_downside = ours["downside_amount"] if ours else None

    if row.get("outcome_id") is None:
        result = "no_outcome"
    elif ours is None:
        result = "not_ranked"
    elif ours["position"] == 1:
        result = "won"
    else:
        result = "lost"

    difference = (
        round(our_downside - winner_downside, 3)
        if result == "lost" and our_downside is not None and winner_downside is not None
        else None
    )
    return {
        "tender_id": row["tender_id"],
        "title": row["title"],
        "cig": row["cig"],
        "status": STATUSES[row["status"]] if row.get("status") is not None and row["status"] < len(STATUSES) else None,
        "base_amount": row.get("base_amount"),
        "submission_deadline": row["submission_deadline"].date() if isinstance(row.get("submission_deadline"), datetime) else row.get("submission_deadline"),
        "contracting_authority": row.get("contracting_authority"),
        "award_date": row.get("award_date"),
        "participants_count": len(participants),
        "our_position": ours["position"] if ours else None,
        "our_downside": our_downside,
        "winner": winner_name if row.get("outcome_id") is not None else None,
        "winner_downside": winner_downside if row.get("outcome_id") is not None else None,
        "difference": difference,
        "result": result,
    }


def summarise(rows: list[dict]) -> dict:
    diffs = [r["difference"] for r in rows if r["difference"] is not None]
    return {
        "tenders": len(rows),
        "with_outcome": sum(r["result"] != "no_outcome" for r in rows),
        "won": sum(r["result"] == "won" for r in rows),
        "lost": sum(r["result"] == "lost" for r in rows),
        "not_ranked": sum(r["result"] == "not_ranked" for r in rows),
        "difference_avg": mean(diffs) if diffs else None,
        "difference_min": min(diffs) if diffs else None,
        "difference_max": max(diffs) if diffs else None,
    }


def my_tenders(f: MyTendersFilters) -> dict:
    if f.azienda_id is None:
        return {"rows": [], "summary": summarise([])}

    with engine.connect() as conn:
        base = [{k: to_plain(v) for k, v in r._mapping.items()} for r in conn.execute(_tenders_query(f))]
        outcome_ids = [r["outcome_id"] for r in base if r["outcome_id"] is not None]
        by_outcome: dict[int, list[dict]] = {}
        if outcome_ids:
            stmt = select(tp.c.tender_outcome_id, tp.c.azienda_id, tp.c.participant, tp.c.downside_amount, tp.c.position).where(
                tp.c.tender_outcome_id.in_(outcome_ids)
            )
            for p in conn.execute(stmt):
                by_outcome.setdefault(p.tender_outcome_id, []).append({k: to_plain(v) for k, v in p._mapping.items()})

    rows = [compare(r, by_outcome.get(r["outcome_id"], []), f.azienda_id) for r in base]
    if f.result:
        rows = [r for r in rows if r["result"] == f.result]
    return {"rows": rows, "summary": summarise(rows)}
