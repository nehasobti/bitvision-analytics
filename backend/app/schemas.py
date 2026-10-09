from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


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


class SavedViewIn(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    filters: dict[str, str] = {}
    group_by: list[str] = []
    measures: list[str] = []


class SavedView(SavedViewIn):
    id: int
    created_at: datetime


class OlapResult(BaseModel):
    group_by: list[str]
    measures: list[str]
    rows: list[dict]
    totals: dict
