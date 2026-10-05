import { useEffect, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, SortChangedEvent } from "ag-grid-community";
import { api, format, type Filters, type Outcome } from "../api";

const PAGE_SIZE = 50;

const COLUMNS: ColDef<Outcome>[] = [
  { field: "successful_tenderer", headerName: "Successful tenderer", flex: 2, minWidth: 180 },
  { field: "contracting_authority", headerName: "Contracting authority", flex: 2, minWidth: 200 },
  { field: "location", headerName: "Location", flex: 1, minWidth: 110 },
  { field: "amount_awarded", headerName: "Amount awarded", flex: 1, minWidth: 150, type: "rightAligned", valueFormatter: (p) => format.money(p.value) },
  { field: "downside_amount", headerName: "Downside", flex: 1, minWidth: 110, type: "rightAligned", valueFormatter: (p) => format.percent(p.value) },
  { field: "publication_date", headerName: "Publication date", flex: 1, minWidth: 130, valueFormatter: (p) => format.date(p.value) },
  { field: "award_date", headerName: "Award date", flex: 1, minWidth: 130, valueFormatter: (p) => format.date(p.value), sort: "desc" },
  { field: "cpv", headerName: "CPV", flex: 1, minWidth: 120 },
];

export default function DataTable({ filters }: { filters: Filters }) {
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
        <h2>Data</h2>
        <span className="muted">{loading ? "Loading…" : `${total.toLocaleString("it-IT")} records`}</span>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="ag-theme-quartz grid">
        <AgGridReact<Outcome>
          rowData={rows}
          columnDefs={COLUMNS}
          defaultColDef={{ resizable: true, sortable: true, wrapHeaderText: true, autoHeaderHeight: true }}
          onSortChanged={onSortChanged}
          overlayNoRowsTemplate="No records match the filters"
        />
      </div>
      <div className="pager">
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <span>Page {page} of {pages}</span>
        <button disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
      </div>
    </section>
  );
}
