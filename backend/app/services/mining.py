"""Data mining on the filtered tender outcomes: finds anomalous values and patterns.

Everything is compared against the filtered data itself (no external baseline).
Outliers use the IQR rule: a value is anomalous when it is more than
`outlier_k` interquartile ranges below Q1 or above Q3. It is robust to a few
extreme values and easy to explain to users.
"""

from collections import defaultdict
from statistics import mean, median, quantiles, stdev

from pydantic import BaseModel, Field

MAX_ROWS = 500  # cap per list returned to the UI / exports


class MiningSettings(BaseModel):
    """Thresholds the user can adjust on the page."""

    outlier_k: float = Field(1.5, ge=0.5, le=10)  # sensitivity of outlier detection
    min_wins: int = Field(3, ge=2, le=1000)  # habitual winner: minimum wins at the same authority
    min_share: float = Field(30, ge=1, le=100)  # habitual winner: minimum % of that authority's awards
    repeat_tolerance: float = Field(0, ge=0, le=5)  # ribasso values within this many points count as equal
    min_repeats: int = Field(3, ge=2, le=1000)  # a ribasso value repeated at least this many times
    max_stdev: float = Field(0.5, ge=0, le=50)  # winner whose ribasso varies less than this (points)


def _fences(values: list[float], k: float) -> dict | None:
    if len(values) < 4:
        return None
    q1, med, q3 = quantiles(values, n=4, method="inclusive")
    iqr = q3 - q1
    return {"q1": q1, "median": med, "q3": q3, "iqr": iqr, "low": q1 - k * iqr, "high": q3 + k * iqr}


def _outliers(rows: list[dict], key: str, fences: dict | None) -> list[dict]:
    """Rows whose `key` falls outside the fences, most extreme first."""
    if not fences:
        return []
    found = []
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        if value > fences["high"]:
            direction, distance = "high", value - fences["high"]
        elif value < fences["low"]:
            direction, distance = "low", fences["low"] - value
        else:
            continue
        score = distance / fences["iqr"] if fences["iqr"] else None
        found.append({**row, "direction": direction, "score": score})
    found.sort(key=lambda r: r["score"] or 0, reverse=True)
    return found[:MAX_ROWS]


def _award_days(row: dict) -> int | None:
    pub, award = row.get("publication_date"), row.get("award_date")
    return (award - pub).days if pub and award else None


def habitual_winners(rows: list[dict], s: MiningSettings) -> list[dict]:
    by_authority: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("contracting_authority") and row.get("successful_tenderer"):
            by_authority[row["contracting_authority"]].append(row)

    found = []
    for authority, awards in by_authority.items():
        wins: dict[str, list[dict]] = defaultdict(list)
        for row in awards:
            wins[row["successful_tenderer"]].append(row)
        for tenderer, won in wins.items():
            share = len(won) / len(awards) * 100
            if len(won) >= s.min_wins and share >= s.min_share:
                found.append({
                    "contracting_authority": authority,
                    "successful_tenderer": tenderer,
                    "wins": len(won),
                    "total_awards": len(awards),
                    "share": share,
                    "amount_awarded": sum(r["amount_awarded"] or 0 for r in won),
                })
    found.sort(key=lambda r: (r["share"], r["wins"]), reverse=True)
    return found[:MAX_ROWS]


def repeated_downside(rows: list[dict], s: MiningSettings) -> list[dict]:
    """The same (or almost the same) ribasso appearing across several awards."""
    values = sorted((r for r in rows if r.get("downside_amount") is not None), key=lambda r: r["downside_amount"])
    groups: list[list[dict]] = []
    for row in values:
        if groups and row["downside_amount"] - groups[-1][0]["downside_amount"] <= s.repeat_tolerance + 1e-9:
            groups[-1].append(row)
        else:
            groups.append([row])

    found = [
        {
            "downside_amount": mean(r["downside_amount"] for r in group),
            "downside_min": group[0]["downside_amount"],
            "downside_max": group[-1]["downside_amount"],
            "count": len(group),
            "tenderers": sorted({r["successful_tenderer"] for r in group if r.get("successful_tenderer")}),
            "authorities": sorted({r["contracting_authority"] for r in group if r.get("contracting_authority")}),
        }
        for group in groups
        if len(group) >= s.min_repeats
    ]
    found.sort(key=lambda r: r["count"], reverse=True)
    return found[:MAX_ROWS]


def consistent_bidders(rows: list[dict], s: MiningSettings) -> list[dict]:
    """Winners whose ribasso is almost the same every time they win."""
    by_tenderer: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row.get("successful_tenderer") and row.get("downside_amount") is not None:
            by_tenderer[row["successful_tenderer"]].append(row["downside_amount"])

    found = []
    for tenderer, values in by_tenderer.items():
        if len(values) < s.min_wins:
            continue
        spread = stdev(values)
        if spread <= s.max_stdev:
            found.append({
                "successful_tenderer": tenderer,
                "wins": len(values),
                "downside_avg": mean(values),
                "downside_min": min(values),
                "downside_max": max(values),
                "downside_stdev": spread,
            })
    found.sort(key=lambda r: r["downside_stdev"])
    return found[:MAX_ROWS]


def analyse(rows: list[dict], s: MiningSettings) -> dict:
    for row in rows:
        row["award_days"] = _award_days(row)

    downside_fences = _fences([r["downside_amount"] for r in rows if r.get("downside_amount") is not None], s.outlier_k)
    # Negative award times are data errors, reported separately and kept out of the baseline.
    valid_days = [r for r in rows if r["award_days"] is not None and r["award_days"] >= 0]
    days_fences = _fences([r["award_days"] for r in valid_days], s.outlier_k)

    return {
        "records": len(rows),
        "settings": s.model_dump(),
        "downside_stats": downside_fences,
        "award_days_stats": days_fences,
        "downside_outliers": _outliers(rows, "downside_amount", downside_fences),
        "award_time_outliers": _outliers(valid_days, "award_days", days_fences),
        "invalid_award_time": [r for r in rows if r["award_days"] is not None and r["award_days"] < 0][:MAX_ROWS],
        "habitual_winners": habitual_winners(rows, s),
        "repeated_downside": repeated_downside(rows, s),
        "consistent_bidders": consistent_bidders(rows, s),
    }
