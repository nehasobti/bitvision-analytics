import { useEffect, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, SortChangedEvent } from "ag-grid-community";
import { api, format, type Filters, type Outcome } from "../api";
import { useT, type Translate } from "../i18n";

const PAGE_SIZE = 50;

const columns = (t: Translate): ColDef<Outcome>[] => [
  { field: "successful_tenderer", headerName: t("fields.successful_tenderer"), flex: 2, minWidth: 180 },
  { field: "contracting_authority", headerName: t("fields.contracting_authority"), flex: 2, minWidth: 200 },
  { field: "location", headerName: t("fields.location"), flex: 1, minWidth: 110 },
  { field: "amount_awarded", headerName: t("fields.amount_awarded"), flex: 1, minWidth: 150, type: "rightAligned", valueFormatter: (p) => format.money(p.value) },
  { field: "downside_amount", headerName: t("fields.downside_amount"), flex: 1, minWidth: 110, type: "rightAligned", valueFormatter: (p) => format.percent(p.value) },
  { field: "publication_date", headerName: t("fields.publication_date"), flex: 1, minWidth: 130, valueFormatter: (p) => format.date(p.value) },
  { field: "award_date", headerName: t("fields.award_date"), flex: 1, minWidth: 130, valueFormatter: (p) => format.date(p.value), sort: "desc" },
  { field: "cpv", headerName: t("fields.cpv"), flex: 1, minWidth: 120 },
];

export default function DataTable({ filters }: { filters: Filters }) {
  const t = useT();
  const columnDefs = useMemo(() => columns(t), [t]);
  const [rows, setRows] = useState<Outcome[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState({ by: "award_date", dir: "desc" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => setPage(1), [filters]);

  useEffect(() => {
    setLoading(true);
    api
      .outcomes(filters, page, PAGE_SIZE, sort.by, sort.dir)
      .then((res) => {
        setRows(res.items);
        setTotal(res.total);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filters, page, sort]);

  const onSortChanged = (e: SortChangedEvent<Outcome>) => {
    const col = e.api.getColumnState().find((c) => c.sort);
    setSort(col ? { by: col.colId, dir: col.sort! } : { by: "award_date", dir: "desc" });
    setPage(1);
  };

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{t("data.title")}</h2>
        <span className="muted">{loading ? t("app.loading") : t("data.records", { count: total.toLocaleString("it-IT") })}</span>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="ag-theme-quartz grid">
        <AgGridReact<Outcome>
          rowData={rows}
          columnDefs={columnDefs}
          defaultColDef={{ resizable: true, sortable: true, wrapHeaderText: true, autoHeaderHeight: true }}
          onSortChanged={onSortChanged}
          overlayNoRowsTemplate={t("data.no_rows")}
        />
      </div>
      <div className="pager">
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>{t("pager.previous")}</button>
        <span>{t("pager.page", { page, pages })}</span>
        <button disabled={page >= pages} onClick={() => setPage(page + 1)}>{t("pager.next")}</button>
      </div>
    </section>
  );
}
