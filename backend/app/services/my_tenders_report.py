"""Layout of the 'Le mie gare' report, shared by the Excel and PDF exports.
Column kinds as in mining_report, plus: status, result (translated) and points (signed number)."""

from app.i18n import t


def columns() -> list[tuple[str, str, str]]:
    return [
        ("title", t("my.col_tender"), "text"),
        ("cig", t("my.col_cig"), "text"),
        ("contracting_authority", t("fields.contracting_authority"), "text"),
        ("status", t("my.col_status"), "status"),
        ("submission_deadline", t("my.col_deadline"), "date"),
        ("base_amount", t("my.col_base_amount"), "money"),
        ("participants_count", t("my.col_participants"), "int"),
        ("our_position", t("my.col_our_position"), "int"),
        ("our_downside", t("my.col_our_downside"), "percent"),
        ("winner", t("fields.successful_tenderer"), "text"),
        ("winner_downside", t("my.col_winner_downside"), "percent"),
        ("difference", t("my.col_difference"), "points"),
        ("result", t("my.col_result"), "result"),
    ]


def summary_rows(summary: dict) -> list[tuple[str, object, str]]:
    return [
        (t("my.sum_tenders"), summary["tenders"], "int"),
        (t("my.sum_with_outcome"), summary["with_outcome"], "int"),
        (t("my.sum_won"), summary["won"], "int"),
        (t("my.sum_lost"), summary["lost"], "int"),
        (t("my.sum_not_ranked"), summary["not_ranked"], "int"),
        (f"{t('my.sum_difference')} – {t('stats.avg')}", summary["difference_avg"], "points"),
        (f"{t('my.sum_difference')} – {t('stats.min')}", summary["difference_min"], "points"),
        (f"{t('my.sum_difference')} – {t('stats.max')}", summary["difference_max"], "points"),
    ]


def filter_rows(filters: dict, azienda_name: str | None) -> list[tuple[str, str]]:
    rows = [(t("my.azienda"), azienda_name or "—")]
    if filters.get("q"):
        rows.append((t("my.search").rstrip("…"), filters["q"]))
    if filters.get("status"):
        names = [t("my.status_concluded") if s == "concluded" else t(f"status.{s}") for s in filters["status"]]
        rows.append((t("my.status"), ", ".join(names)))
    if filters.get("result"):
        rows.append((t("my.result"), t(f"my.{filters['result']}")))
    if filters.get("deadline_from"):
        rows.append((f"{t('my.deadline')} ({t('filters.from')})", filters["deadline_from"].strftime("%d/%m/%Y")))
    if filters.get("deadline_to"):
        rows.append((f"{t('my.deadline')} ({t('filters.to')})", filters["deadline_to"].strftime("%d/%m/%Y")))
    return rows
