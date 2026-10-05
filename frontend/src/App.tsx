import { useEffect, useState } from "react";
import { api, type Analysis, type Filters, type Meta } from "./api";
import FiltersPanel from "./components/FiltersPanel";
import DataTable from "./components/DataTable";
import OlapPanel from "./components/OlapPanel";

type Tab = "data" | "analysis";

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [analysis, setAnalysis] = useState<Analysis>({
    groupBy: ["contracting_authority"],
    measures: ["amount_awarded", "downside_amount"],
  });
  const [tab, setTab] = useState<Tab>("data");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.meta().then(setMeta).catch((e: Error) => setError(e.message));
  }, []);

  const canExport = analysis.measures.length > 0;

  return (
    <div className="layout">
      <header className="topbar">
        <h1>BitVision Analytics · Tender outcomes</h1>
        <div className="exports">
          <a className={`button ${canExport ? "" : "disabled"}`} href={api.exportUrl("excel", filters, analysis)}>
            Export Excel
          </a>
          <a className={`button ${canExport ? "" : "disabled"}`} href={api.exportUrl("pdf", filters, analysis)}>
            Export PDF
          </a>
        </div>
      </header>

      <FiltersPanel onApply={setFilters} />

      <main>
        <nav className="tabs">
          <button className={tab === "data" ? "active" : ""} onClick={() => setTab("data")}>Data</button>
          <button className={tab === "analysis" ? "active" : ""} onClick={() => setTab("analysis")}>Analysis</button>
        </nav>

        {error && <p className="error">Cannot reach the API: {error}</p>}
        {tab === "data" && <DataTable filters={filters} />}
        {tab === "analysis" && meta && (
          <OlapPanel meta={meta} filters={filters} analysis={analysis} onChange={setAnalysis} />
        )}
      </main>
    </div>
  );
}
