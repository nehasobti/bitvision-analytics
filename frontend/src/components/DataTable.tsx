import { useEffect, useMemo, useRef, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, GridApi, RowDataUpdatedEvent, SelectionChangedEvent, SortChangedEvent } from "ag-grid-community";
import { api, format, type Filters, type Outcome } from "../api";
import { useT, type Translate } from "../i18n";

const PAGE_SIZE = 50;

// Selection changes made by the user (not by the grid reloading rows or by our own code).
const USER_SOURCES = new Set(["checkboxSelected", "rowClicked", "uiSelectAll", "uiSelectAllCurrentPage", "uiSelectAllFiltered", "spaceKey"]);

type Stats = { avg: number; min: number; max: number } | null;

function stats(values: (number | null)[]): Stats {
  const nums = values.filter((v): v is number => typeof v === "number");
  if (nums.length === 0) return null;
  return { avg: nums.reduce((a, b) => a + b, 0) / nums.length, min: Math.min(...nums), max: Math.max(...nums) };
}

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
  // Selected rows by id; kept across pages and sorting.
  const [selected, setSelected] = useState<Map<number, Outcome>>(new Map());
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const gridApi = useRef<GridApi<Outcome> | null>(null);

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

  const onSelectionChanged = (e: SelectionChangedEvent<Outcome>) => {
    if (!USER_SOURCES.has(e.source)) return;
    const next = new Map(selectedRef.current);
    e.api.forEachNode((node) => {
      if (!node.data) return;
      if (node.isSelected()) next.set(node.data.id, node.data);
      else next.delete(node.data.id);
    });
    setSelected(next);
  };

  // A new page/sort replaces the rows: tick again the ones selected before.
  const onRowDataUpdated = (e: RowDataUpdatedEvent<Outcome>) => {
    e.api.forEachNode((node) => {
      if (node.data) node.setSelected(selectedRef.current.has(node.data.id), false, "api");
    });
  };

  const clearSelection = () => {
    setSelected(new Map());
    gridApi.current?.deselectAll("api");
  };

  const summary = useMemo(() => {
    const items = [...selected.values()];
    return {
      amount: stats(items.map((r) => r.amount_awarded)),
      downside: stats(items.map((r) => r.downside_amount)),
    };
  }, [selected]);

  const statGroup = (label: string, s: Stats, fmt: (v: unknown) => string) => (
    <div className="stat-group">
      <span>{label}:</span>
      <span>{t("stats.avg")} <strong>{s ? fmt(s.avg) : "—"}</strong></span>
      <span>{t("stats.min")} <strong>{s ? fmt(s.min) : "—"}</strong></span>
      <span>{t("stats.max")} <strong>{s ? fmt(s.max) : "—"}</strong></span>
    </div>
  );

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{t("data.title")}</h2>
        <span className="muted">{loading ? t("app.loading") : t("data.records", { count: total.toLocaleString("it-IT") })}</span>
      </div>
      {error && <p className="error">{error}</p>}
      {selected.size > 0 ? (
        <div className="selection-summary">
          <strong>{t("selection.count", { count: selected.size })}</strong>
          {statGroup(t("fields.amount_awarded"), summary.amount, format.money)}
          {statGroup(t("fields.downside_amount"), summary.downside, format.percent)}
          <button type="button" onClick={clearSelection}>{t("selection.clear")}</button>
        </div>
      ) : (
        <p className="muted">{t("selection.hint")}</p>
      )}
      <div className="ag-theme-quartz grid">
        <AgGridReact<Outcome>
          rowData={rows}
          columnDefs={columnDefs}
          defaultColDef={{ resizable: true, sortable: true, wrapHeaderText: true, autoHeaderHeight: true }}
          getRowId={(p) => String(p.data.id)}
          rowSelection={{ mode: "multiRow", checkboxes: true, headerCheckbox: true, enableClickSelection: false }}
          onGridReady={(e) => (gridApi.current = e.api)}
          onSelectionChanged={onSelectionChanged}
          onRowDataUpdated={onRowDataUpdated}
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
