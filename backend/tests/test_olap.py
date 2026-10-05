from datetime import date

import pytest
from sqlalchemy.dialects import mysql

from app.schemas import OutcomeFilters
from app.services.olap import OlapError, build_query, validate


def sql(stmt) -> str:
    return str(stmt.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))


def test_group_by_selected_dimensions():
    query = sql(build_query(OutcomeFilters(), ["contracting_authority", "award_year"]))
    assert "GROUP BY" in query
    assert "year(tender_outcomes.award_date)" in query
    for stat in ("avg", "min", "max"):
        assert f"{stat}(tender_outcomes.amount_awarded)" in query
        assert f"{stat}(tender_outcomes.downside_amount)" in query


def test_no_group_by_returns_single_total():
    assert "GROUP BY" not in sql(build_query(OutcomeFilters(), []))


def test_filters_are_applied():
    filters = OutcomeFilters(location="Salerno", cpv="4523", award_date_from=date(2024, 1, 1))
    query = sql(build_query(filters, ["location"]))
    assert "tender_outcomes.location LIKE" in query
    assert "tender_outcomes.cpv LIKE concat('4523'" in query
    assert "tender_outcomes.award_date >= '2024-01-01'" in query


@pytest.mark.parametrize(
    "group_by, measures",
    [(["unknown"], ["amount_awarded"]), (["cpv", "cpv"], ["amount_awarded"]), (["cpv"], []), ([], ["bad"])],
)
def test_invalid_requests_are_rejected(group_by, measures):
    with pytest.raises(OlapError):
        validate(group_by, measures)
