import { useEffect, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef } from "ag-grid-community";
import {
  api,
  format,
  type Azienda,
  type Meta,
  type MyTenderRow,
  type MyTendersFilters,
  type MyTendersSummary,
} from "../api";
import { useT, type Translate } from "../i18n";

const RESULTS = ["won", "lost", "not_ranked", "no_outcome"] as const;

const columns = (t: Translate): ColDef<MyTenderRow>[] => [
  { field: "title", headerName: t("my.col_tender"), pinned: "left", minWidth: 220, flex: 2, tooltipField: "title" },
  { field: "cig", headerName: t("my.col_cig"), minWidth: 120 },
  { field: "contracting_authority", headerName: t("fields.contracting_authority"), minWidth: 180, flex: 1 },
  { field: "status", headerName: t("my.col_status"), minWidth: 130, valueFormatter: (p) => (p.value ? t(`status.${p.value}`) : "") },
  { field: "submission_deadline", headerName: t("my.col_deadline"), minWidth: 120, valueFormatter: (p) => format.date(p.value) },
  { field: "participants_count", headerName: t("my.col_participants"), type: "rightAligned", minWidth: 110 },
  { field: "our_position", headerName: t("my.col_our_position"), type: "rightAligned", minWidth: 120 },
  { field: "our_downside", headerName: t("my.col_our_downside"), type: "rightAligned", minWidth: 130, valueFormatter: (p) => format.percent(p.value) },
  { field: "winner", headerName: t("fields.successful_tenderer"), minWidth: 180, flex: 1 },
  { field: "winner_downside", headerName: t("my.col_winner_downside"), type: "rightAligned", minWidth: 150, valueFormatter: (p) => format.percent(p.value) },
  {
    field: "difference",
    headerName: t("my.col_difference"),
    type: "rightAligned",
    minWidth: 140,
    valueFormatter: (p) => format.points(p.value),
    cellClass: (p) => (typeof p.value === "number" ? (p.value < 0 ? "diff-negative" : "diff-positive") : ""),
  },
  {
    field: "result",
    headerName: t("my.col_result"),
    minWidth: 170,
    cellRenderer: (p: { value: string }) => <span className={`badge badge-${p.value}`}>{t(`my.${p.value}`)}</span>,
  },
];

// "Le mie gare": tenders the selected company took part in, comparing our ribasso with the winner's.
export default function MyTenders({ meta }: { meta: Meta }) {
  const t = useT();
  const columnDefs = useMemo(() => columns(t), [t]);
  const [aziende, setAziende] = useState<Azienda[]>([]);
  const [filters, setFilters] = useState<MyTendersFilters>({});
  const [search, setSearch] = useState("");
  const [rows, setRows] = useState<MyTenderRow[]>([]);
  const [summary, setSummary] = useState<MyTendersSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .aziende()
      .then((list) => {
        setAziende(list);
        if (list.length > 0) setFilters((f) => ({ ...f, azienda_id: f.azienda_id ?? list[0].id }));
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  // Search text is applied shortly after the user stops typing.
  useEffect(() => {
    const timer = setTimeout(() => setFilters((f) => ({ ...f, q: search.trim() || undefined })), 400);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (filters.azienda_id === undefined) return;
    setLoading(true);
    api
      .myTenders(filters)
      .then((res) => {
        setRows(res.rows);
        setSummary(res.summary);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filters]);

  const set = (patch: Partial<MyTendersFilters>) => setFilters({ ...filters, ...patch });

  const reset = () => {
    setSearch("");
    setFilters({ azienda_id: filters.azienda_id });
  };

  const tile = (label: string, value: string | number) => (
    <div className="tile">
      <span className="tile-label">{label}</span>
      <strong className="tile-value">{value}</strong>
    </div>
  );

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{t("my.title")}</h2>
        <div className="exports">
          <a className={`button ${filters.azienda_id ? "" : "disabled"}`} href={api.myTendersExportUrl("excel", filters)}>{t("export.excel")}</a>
          <a className={`button ${filters.azienda_id ? "" : "disabled"}`} href={api.myTendersExportUrl("pdf", filters)}>{t("export.pdf")}</a>
        </div>
      </div>

      <div className="my-filters">
        <label>
          <span>{t("my.azienda")}</span>
          <select value={filters.azienda_id ?? ""} onChange={(e) => set({ azienda_id: e.target.value ? Number(e.target.value) : undefined })}>
            {aziende.length === 0 && <option value="">{t("my.no_azienda")}</option>}
            {aziende.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </label>
        <label className="wide">
          <span>&nbsp;</span>
          <input value={search} placeholder={t("my.search")} onChange={(e) => setSearch(e.target.value)} />
        </label>
        <label>
          <span>{t("my.status")}</span>
          <select value={filters.status ?? ""} onChange={(e) => set({ status: e.target.value || undefined })}>
            <option value="">{t("my.status_all")}</option>
            <option value="concluded">{t("my.status_concluded")}</option>
            {meta.tender_statuses.map((s) => <option key={s} value={s}>{t(`status.${s}`)}</option>)}
          </select>
        </label>
        <label>
          <span>{t("my.result")}</span>
          <select value={filters.result ?? ""} onChange={(e) => set({ result: (e.target.value || undefined) as MyTendersFilters["result"] })}>
            <option value="">{t("my.result_all")}</option>
            {RESULTS.map((r) => <option key={r} value={r}>{t(`my.${r}`)}</option>)}
          </select>
        </label>
        <label>
          <span>{t("my.deadline")} · {t("filters.from")}</span>
          <input type="date" value={filters.deadline_from ?? ""} onChange={(e) => set({ deadline_from: e.target.value || undefined })} />
        </label>
        <label>
          <span>{t("filters.to")}</span>
          <input type="date" value={filters.deadline_to ?? ""} onChange={(e) => set({ deadline_to: e.target.value || undefined })} />
        </label>
        <button type="button" onClick={reset}>{t("my.reset")}</button>
      </div>

      {error && <p className="error">{error}</p>}

      {summary && (
        <div className="tiles">
          {tile(t("my.sum_tenders"), summary.tenders)}
          {tile(t("my.sum_with_outcome"), summary.with_outcome)}
          {tile(t("my.sum_won"), summary.won)}
          {tile(t("my.sum_lost"), summary.lost)}
          {tile(`${t("my.sum_difference")} · ${t("stats.avg")}`, format.points(summary.difference_avg) || "—")}
          {tile(`${t("stats.min")} / ${t("stats.max")}`, summary.difference_min === null ? "—" : `${format.points(summary.difference_min)} / ${format.points(summary.difference_max)}`)}
        </div>
      )}
      <p className="muted">{loading ? t("app.loading") : t("my.hint")}</p>

      <div className="ag-theme-quartz grid">
        <AgGridReact<MyTenderRow>
          rowData={rows}
          columnDefs={columnDefs}
          getRowId={(p) => String(p.data.tender_id)}
          defaultColDef={{ resizable: true, sortable: true, wrapHeaderText: true, autoHeaderHeight: true }}
          overlayNoRowsTemplate={t("my.none")}
        />
      </div>
    </section>
  );
}
