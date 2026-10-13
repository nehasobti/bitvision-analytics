"""Layout of the data mining report, shared by the Excel and PDF exports."""

from app.i18n import t

# Column kinds: money, percent, date, int, number, text, list, direction


def _num(value, decimals: int) -> str:
    return "—" if value is None else f"{value:.{decimals}f}".replace(".", ",")


def _hint_range(stats: dict | None, key: str, decimals: int) -> str:
    if not stats:
        return t("mining.not_enough")
    # Ribasso and days are never negative, so a negative lower fence is shown as 0.
    low = max(stats["low"], 0)
    return t(key, low=_num(low, decimals), high=_num(stats["high"], decimals), median=_num(stats["median"], decimals))


def sections(result: dict) -> list[dict]:
    s = result["settings"]
    outcome_cols = [
        ("successful_tenderer", t("fields.successful_tenderer"), "text"),
        ("contracting_authority", t("fields.contracting_authority"), "text"),
        ("location", t("fields.location"), "text"),
        ("amount_awarded", t("fields.amount_awarded"), "money"),
        ("downside_amount", t("fields.downside_amount"), "percent"),
        ("publication_date", t("fields.publication_date"), "date"),
        ("award_date", t("fields.award_date"), "date"),
        ("cpv", t("fields.cpv"), "text"),
    ]
    return [
        {
            "key": "downside_outliers",
            "title": t("mining.downside_outliers"),
            "hint": _hint_range(result["downside_stats"], "mining.downside_hint", 3),
            "columns": [("direction", t("mining.col_direction"), "direction"), ("score", t("mining.col_score"), "number"), *outcome_cols],
            "rows": result["downside_outliers"],
        },
        {
            "key": "award_time_outliers",
            "title": t("mining.award_time_outliers"),
            "hint": _hint_range(result["award_days_stats"], "mining.award_time_hint", 0),
            "columns": [
                ("direction", t("mining.col_direction"), "direction"),
                ("award_days", t("mining.col_award_days"), "int"),
                ("score", t("mining.col_score"), "number"),
                *outcome_cols,
            ],
            "rows": result["award_time_outliers"],
        },
        {
            "key": "invalid_award_time",
            "title": t("mining.invalid_award_time"),
            "hint": "",
            "columns": [("award_days", t("mining.col_award_days"), "int"), *outcome_cols],
            "rows": result["invalid_award_time"],
        },
        {
            "key": "habitual_winners",
            "title": t("mining.habitual_winners"),
            "hint": t("mining.habitual_hint", min_wins=s["min_wins"], min_share=_num(s["min_share"], 0)),
            "columns": [
                ("contracting_authority", t("fields.contracting_authority"), "text"),
                ("successful_tenderer", t("fields.successful_tenderer"), "text"),
                ("wins", t("mining.col_wins"), "int"),
                ("total_awards", t("mining.col_total_awards"), "int"),
                ("share", t("mining.col_share"), "percent"),
                ("amount_awarded", t("fields.amount_awarded"), "money"),
            ],
            "rows": result["habitual_winners"],
        },
        {
            "key": "repeated_downside",
            "title": t("mining.repeated_downside"),
            "hint": t("mining.repeated_hint", tolerance=_num(s["repeat_tolerance"], 3), min_repeats=s["min_repeats"]),
            "columns": [
                ("downside_amount", t("fields.downside_amount"), "percent"),
                ("count", t("mining.col_count"), "int"),
                ("tenderers", t("mining.col_tenderers"), "list"),
                ("authorities", t("mining.col_authorities"), "list"),
            ],
            "rows": result["repeated_downside"],
        },
        {
            "key": "consistent_bidders",
            "title": t("mining.consistent_bidders"),
            "hint": t("mining.consistent_hint", min_wins=s["min_wins"], max_stdev=_num(s["max_stdev"], 3)),
            "columns": [
                ("successful_tenderer", t("fields.successful_tenderer"), "text"),
                ("wins", t("mining.col_wins"), "int"),
                ("downside_avg", f"{t('fields.downside_amount')} – {t('stats.avg')}", "percent"),
                ("downside_min", f"{t('fields.downside_amount')} – {t('stats.min')}", "percent"),
                ("downside_max", f"{t('fields.downside_amount')} – {t('stats.max')}", "percent"),
                ("downside_stdev", t("mining.col_stdev"), "number"),
            ],
            "rows": result["consistent_bidders"],
        },
    ]


def settings_rows(result: dict) -> list[tuple[str, object]]:
    return [(t(f"mining.{k}"), v) for k, v in result["settings"].items()]
