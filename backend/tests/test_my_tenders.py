from datetime import datetime

from sqlalchemy.dialects import mysql

from app.services.my_tenders import MyTendersFilters, _status_codes, _tenders_query, compare, summarise

OURS = 9


def tender(outcome_id=10, successful_tenderer="Rossi", outcome_downside=20.0, status=6):
    return {
        "tender_id": 1, "title": "Gara", "cig": "CIG1", "status": status, "base_amount": 1000.0,
        "submission_deadline": datetime(2026, 5, 1, 12, 0), "contracting_authority": "Comune",
        "outcome_id": outcome_id, "successful_tenderer": successful_tenderer,
        "outcome_downside": outcome_downside, "award_date": None,
    }


def p(name, position, downside, azienda_id=None):
    return {"participant": name, "position": position, "downside_amount": downside, "azienda_id": azienda_id}


def test_lost_tender_compares_with_position_1():
    row = compare(tender(), [p("Rossi", 1, 18.5), p("Noi", 2, 15.2, OURS), p("Altri", 3, 12.0)], OURS)
    assert row["result"] == "lost"
    assert (row["winner"], row["winner_downside"], row["our_position"], row["our_downside"]) == ("Rossi", 18.5, 2, 15.2)
    assert row["difference"] == -3.3
    assert row["participants_count"] == 3 and row["status"] == "awarded"
    assert row["submission_deadline"].isoformat() == "2026-05-01"


def test_won_tender_has_no_difference():
    row = compare(tender(), [p("Noi", 1, 21.0, OURS), p("Rossi", 2, 18.0)], OURS)
    assert row["result"] == "won" and row["difference"] is None and row["winner"] == "Noi"


def test_outcome_without_our_row_and_without_score_list():
    row = compare(tender(), [], OURS)
    assert row["result"] == "not_ranked"
    assert (row["winner"], row["winner_downside"]) == ("Rossi", 20.0)  # falls back to the outcome fields


def test_tender_without_outcome():
    row = compare(tender(outcome_id=None, successful_tenderer=None, outcome_downside=None), [], OURS)
    assert row["result"] == "no_outcome" and row["winner"] is None and row["participants_count"] == 0


def test_summary_counts_and_differences():
    rows = [
        compare(tender(), [p("R", 1, 20.0), p("Noi", 2, 15.0, OURS)], OURS),
        compare(tender(), [p("R", 1, 20.0), p("Noi", 3, 19.0, OURS)], OURS),
        compare(tender(), [p("Noi", 1, 22.0, OURS)], OURS),
        compare(tender(outcome_id=None), [], OURS),
    ]
    s = summarise(rows)
    assert (s["tenders"], s["with_outcome"], s["won"], s["lost"], s["not_ranked"]) == (4, 3, 1, 2, 0)
    assert (s["difference_min"], s["difference_max"], s["difference_avg"]) == (-5.0, -1.0, -3.0)


def test_status_filter_and_company_scope_in_sql():
    assert sorted(_status_codes(["concluded"])) == [6, 7, 8]
    sql = str(_tenders_query(MyTendersFilters(azienda_id=9, status=["concluded"], q="ponte")).compile(
        dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "tender_bookmarks" in sql and "tender_participants" in sql and "users.azienda_id = 9" in sql
    assert "tenders.status IN (" in sql and "LEFT OUTER JOIN tender_outcomes" in sql
