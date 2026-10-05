import { useEffect, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, ColGroupDef } from "ag-grid-community";
import { api, format, type Analysis, type Filters, type Meta, type OlapResult, type OlapRow } from "../api";

interface Props {
  meta: Meta;
  filters: Filters;
  analysis: Analysis;
  onChange: (analysis: Analysis) => void;
}

const STAT_LABELS: Record<string, string> = { avg: "Average", min: "Min", max: "Max" };

export default function OlapPanel({ meta, filters, analysis, onChange }: Props) {
  const [result, setResult] = useState<OlapResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (analysis.measures.length === 0) return;
    api
      .olap(filters, analysis)
      .then((res) => {
        setResult(res);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [filters, analysis]);

  // Order of clicks = order of grouping levels.
  const toggleDimension = (key: string) =>
    onChange({
      ...analysis,
      groupBy: analysis.groupBy.includes(key)
        ? analysis.groupBy.filter((g) => g !== key)
        : [...analysis.groupBy, key],
    });

  const toggleMeasure = (key: string) =>
    onChange({
      ...analysis,
      // Keep measures in a fixed order, whatever the click order.
      measures: meta.measures
        .map((m) => m.key)
        .filter((m) => (m === key ? !analysis.measures.includes(key) : analysis.measures.includes(m))),
    });

  const columns = useMemo<(ColDef<OlapRow> | ColGroupDef<OlapRow>)[]>(() => {
    if (!result) return [];
    const label = (key: string, list: { key: string; label: string }[]) =>
      list.find((o) => o.key === key)?.label ?? key;
    return [
      ...(result.group_by.length
        ? result.group_by.map((g) => ({ field: g, headerName: label(g, meta.dimensions), pinned: "left" as const, minWidth: 160 }))
        : [{ headerName: "", valueGetter: () => "All records", minWidth: 160 }]),
      { field: "count", headerName: "Count", type: "rightAligned", minWidth: 90, flex: 0 },
      ...result.measures.map((m) => ({
        headerName: label(m, meta.measures),
        children: meta.stats.map((s) => ({
          field: `${m}_${s}`,
          headerName: STAT_LABELS[s] ?? s,
          type: "rightAligned",
          minWidth: 130,
          valueFormatter: (p: { value: unknown }) =>
            m === "amount_awarded" ? format.money(p.value) : format.percent(p.value),
        })),
      })),
    ];
  }, [result, meta]);

  const totalsRow = result ? [{ ...result.totals, ...Object.fromEntries(result.group_by.map((g, i) => [g, i === 0 ? "Total" : ""])) }] : [];

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Analysis</h2>
      </div>

      <div className="olap-controls">
        <div>
          <span className="control-label">Group by (click in order)</span>
          <div className="chips">
            {meta.dimensions.map((d) => {
              const level = analysis.groupBy.indexOf(d.key);
              return (
                <button
                  key={d.key}
                  className={`chip ${level >= 0 ? "active" : ""}`}
                  onClick={() => toggleDimension(d.key)}
                >
                  {level >= 0 && <span className="level">{level + 1}</span>}
                  {d.label}
                </button>
              );
            })}
          </div>
        </div>
        <div>
          <span className="control-label">Measures (average, min, max)</span>
          <div className="chips">
            {meta.measures.map((m) => (
              <button
                key={m.key}
                className={`chip ${analysis.measures.includes(m.key) ? "active" : ""}`}
                onClick={() => toggleMeasure(m.key)}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {analysis.measures.length === 0 && <p className="muted">Select at least one measure.</p>}
      {error && <p className="error">{error}</p>}

      {result && analysis.measures.length > 0 && (
        <div className="ag-theme-quartz grid">
          <AgGridReact<OlapRow>
            rowData={result.rows}
            columnDefs={columns}
            pinnedBottomRowData={totalsRow}
            defaultColDef={{ resizable: true, sortable: true, flex: 1 }}
            overlayNoRowsTemplate={result.group_by.length ? "No data for this selection" : "Choose fields to group by"}
          />
        </div>
      )}
    </section>
  );
}
