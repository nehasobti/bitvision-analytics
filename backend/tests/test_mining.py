from datetime import date

from app.services.mining import MiningSettings, analyse


def row(id, tenderer="A", authority="X", downside=10.0, pub=date(2024, 1, 1), award=date(2024, 3, 1), amount=1000.0):
    return {
        "id": id,
        "successful_tenderer": tenderer,
        "contracting_authority": authority,
        "location": "Roma",
        "amount_awarded": amount,
        "downside_amount": downside,
        "publication_date": pub,
        "award_date": award,
        "cpv": "45000000",
    }


def test_downside_outliers_high_and_low():
    rows = [row(i, downside=10 + i * 0.5) for i in range(10)] + [row(98, downside=60.0), row(99, downside=-90.0)]
    result = analyse(rows, MiningSettings())
    found = {r["id"]: r["direction"] for r in result["downside_outliers"]}
    assert found == {98: "high", 99: "low"}
    assert result["downside_outliers"][0]["id"] == 99  # most extreme first


def test_award_time_outliers_and_invalid_dates():
    rows = [row(i, award=date(2024, 3, 1 + i)) for i in range(10)]
    rows.append(row(50, award=date(2026, 1, 1)))  # very slow
    rows.append(row(51, pub=date(2024, 5, 1), award=date(2024, 4, 1)))  # award before publication
    result = analyse(rows, MiningSettings())
    assert [r["id"] for r in result["award_time_outliers"]] == [50]
    assert [r["id"] for r in result["invalid_award_time"]] == [51]


def test_habitual_winner_respects_thresholds():
    rows = [row(i, tenderer="Big", authority="X") for i in range(4)] + [row(10 + i, tenderer=f"T{i}", authority="X") for i in range(6)]
    found = analyse(rows, MiningSettings(min_wins=3, min_share=30))["habitual_winners"]
    assert [(r["successful_tenderer"], r["wins"], r["total_awards"]) for r in found] == [("Big", 4, 10)]
    assert analyse(rows, MiningSettings(min_wins=3, min_share=50))["habitual_winners"] == []


def test_repeated_downside_with_tolerance():
    rows = [row(1, downside=12.345), row(2, downside=12.345), row(3, downside=12.345), row(4, downside=12.4), row(5, downside=20.0)]
    exact = analyse(rows, MiningSettings(min_repeats=3))["repeated_downside"]
    assert [(r["count"], r["downside_min"], r["downside_max"]) for r in exact] == [(3, 12.345, 12.345)]
    loose = analyse(rows, MiningSettings(min_repeats=3, repeat_tolerance=0.1))["repeated_downside"]
    assert loose[0]["count"] == 4


def test_consistent_bidders():
    rows = [row(i, tenderer="Steady", downside=15.0 + i * 0.01) for i in range(4)]
    rows += [row(10 + i, tenderer="Varied", downside=5.0 + i * 10) for i in range(4)]
    found = analyse(rows, MiningSettings(min_wins=3, max_stdev=0.5))["consistent_bidders"]
    assert [r["successful_tenderer"] for r in found] == ["Steady"]


def test_too_few_records_gives_no_outliers():
    result = analyse([row(1), row(2)], MiningSettings())
    assert result["downside_outliers"] == [] and result["downside_stats"] is None
