from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.config import settings
from app.i18n import dimension_label, field_labels, messages, t
from app import saved_views
from app.schemas import OlapResult, OutcomeFilters, OutcomePage, SavedView, SavedViewIn
from app.services import olap as olap_service
from app.services.export_excel import build_excel
from app.services.export_pdf import build_mining_pdf, build_my_tenders_pdf, build_pdf
from app.services.export_excel import build_mining_excel, build_my_tenders_excel
from app.services.mining import MiningSettings, analyse
from app.services.mining_report import sections
from app.services import my_tenders as my_tenders_service
from app.services.outcomes import all_outcomes, list_outcomes

router = APIRouter(prefix="/api")

Filters = Annotated[OutcomeFilters, Depends()]
GroupBy = Annotated[list[str], Query()]
Measures = Annotated[list[str], Query()]
DEFAULT_MEASURES = list(olap_service.MEASURES)


@router.get("/meta")
def meta():
    """Fields the frontend can offer for grouping and aggregation, plus all UI texts."""
    return {
        "language": settings.app_language,
        "messages": messages(),
        "fields": field_labels(),
        "dimensions": [{"key": k, "label": dimension_label(k)} for k in olap_service.DIMENSIONS],
        "measures": [{"key": k, "label": t(f"fields.{k}")} for k in olap_service.MEASURES],
        "stats": list(olap_service.STATS),
        "tender_statuses": my_tenders_service.STATUSES,
    }


@router.get("/outcomes", response_model=OutcomePage)
def outcomes(
    filters: Filters,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
    sort_by: str = "award_date",
    sort_dir: Literal["asc", "desc"] = "desc",
):
    total, items = list_outcomes(filters, page, page_size, sort_by, sort_dir)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


def _olap(filters: OutcomeFilters, group_by: list[str], measures: list[str]) -> dict:
    try:
        return olap_service.run_olap(filters, group_by, measures or DEFAULT_MEASURES)
    except olap_service.OlapError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/olap", response_model=OlapResult)
def olap(filters: Filters, group_by: GroupBy = [], measures: Measures = []):
    return _olap(filters, group_by, measures)


@router.get("/saved-views", response_model=list[SavedView])
def list_saved_views():
    return saved_views.list_views()


@router.post("/saved-views", response_model=SavedView, status_code=201)
def create_saved_view(view: SavedViewIn):
    unknown = [k for k in view.filters if k not in OutcomeFilters.model_fields]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown filter(s): {', '.join(unknown)}")
    _olap_check(view.group_by, view.measures)
    return saved_views.create_view(view.description.strip(), view.filters, view.group_by, view.measures)


@router.delete("/saved-views/{view_id}", status_code=204)
def delete_saved_view(view_id: int):
    if not saved_views.delete_view(view_id):
        raise HTTPException(status_code=404, detail="Saved view not found")


def _olap_check(group_by: list[str], measures: list[str]) -> None:
    try:
        olap_service.validate(group_by, measures)
    except olap_service.OlapError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _file_name(ext: str, name_key: str = "report.file_name") -> str:
    return f"{t(name_key)}_{datetime.now():%Y%m%d_%H%M}.{ext}"


Mining = Annotated[MiningSettings, Query()]


def _mining(filters: OutcomeFilters, mining: MiningSettings) -> dict:
    return analyse(all_outcomes(filters, settings.export_max_rows), mining)


@router.get("/mining")
def mining_report(filters: Filters, mining: Mining):
    """Anomalies in the filtered data, laid out as report sections (same as the exports)."""
    result = _mining(filters, mining)
    return {"records": result["records"], "settings": result["settings"], "sections": sections(result)}


@router.get("/mining/export/excel")
def mining_export_excel(filters: Filters, mining: Mining):
    content = build_mining_excel(_mining(filters, mining), filters.active())
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{_file_name("xlsx", "mining.file_name")}"'},
    )


@router.get("/mining/export/pdf")
def mining_export_pdf(filters: Filters, mining: Mining):
    content = build_mining_pdf(_mining(filters, mining), filters.active())
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_file_name("pdf", "mining.file_name")}"'},
    )


MyTenders = Annotated[my_tenders_service.MyTendersFilters, Query()]


@router.get("/my-tenders/aziende")
def my_tenders_aziende():
    """Companies the user can pick in 'Le mie gare' (the app has no login)."""
    return my_tenders_service.list_aziende()


@router.get("/my-tenders")
def my_tenders(filters: MyTenders):
    """Tenders the company took part in, with our ribasso vs the winner's."""
    return my_tenders_service.my_tenders(filters)


def _azienda_name(azienda_id: int | None) -> str | None:
    return next((a["name"] for a in my_tenders_service.list_aziende() if a["id"] == azienda_id), None)


@router.get("/my-tenders/export/excel")
def my_tenders_export_excel(filters: MyTenders):
    result = my_tenders_service.my_tenders(filters)
    content = build_my_tenders_excel(result, filters.active(), _azienda_name(filters.azienda_id))
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{_file_name("xlsx", "my.file_name")}"'},
    )


@router.get("/my-tenders/export/pdf")
def my_tenders_export_pdf(filters: MyTenders):
    result = my_tenders_service.my_tenders(filters)
    content = build_my_tenders_pdf(result, filters.active(), _azienda_name(filters.azienda_id))
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_file_name("pdf", "my.file_name")}"'},
    )


@router.get("/export/excel")
def export_excel(filters: Filters, group_by: GroupBy = [], measures: Measures = []):
    result = _olap(filters, group_by, measures)
    content = build_excel(all_outcomes(filters, settings.export_max_rows), result, filters.active())
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{_file_name("xlsx")}"'},
    )


@router.get("/export/pdf")
def export_pdf(filters: Filters, group_by: GroupBy = [], measures: Measures = []):
    result = _olap(filters, group_by, measures)
    content = build_pdf(all_outcomes(filters, settings.export_max_rows), result, filters.active())
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_file_name("pdf")}"'},
    )
