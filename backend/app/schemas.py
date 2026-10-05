from datetime import date
from decimal import Decimal

from pydantic import BaseModel

# Human-readable labels, shared by the API, Excel and PDF exports.
FIELD_LABELS = {
    "successful_tenderer": "Successful tenderer",
    "contracting_authority": "Contracting authority",
    "location": "Location",
    "amount_awarded": "Amount awarded (€)",
    "downside_amount": "Downside (%)",
    "publication_date": "Publication date",
    "award_date": "Award date",
    "cpv": "CPV",
}


class OutcomeFilters(BaseModel):
    successful_tenderer: str | None = None
    contracting_authority: str | None = None
    location: str | None = None
    cpv: str | None = None
    amount_awarded_min: Decimal | None = None
    amount_awarded_max: Decimal | None = None
    downside_min: Decimal | None = None
    downside_max: Decimal | None = None
    publication_date_from: date | None = None
    publication_date_to: date | None = None
    award_date_from: date | None = None
    award_date_to: date | None = None

    def active(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v not in (None, "")}


class Outcome(BaseModel):
    id: int
    successful_tenderer: str | None
    contracting_authority: str | None
    location: str | None
    amount_awarded: float | None
    downside_amount: float | None
    publication_date: date | None
    award_date: date | None
    cpv: str | None


class OutcomePage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[Outcome]


class OlapResult(BaseModel):
    group_by: list[str]
    measures: list[str]
    rows: list[dict]
    totals: dict
