import { useEffect, useMemo, useState } from "react";
import { api, type Analysis, type Filters, type Meta } from "./api";
import { I18nProvider, makeTranslate } from "./i18n";
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

  const t = useMemo(() => makeTranslate(meta?.messages ?? {}), [meta]);

  useEffect(() => {
    if (!meta) return;
    document.documentElement.lang = meta.language;
    document.title = t("app.title");
  }, [meta, t]);

  // Texts come with /api/meta, so nothing is shown until it has loaded.
  if (!meta) {
    return <p className={error ? "error" : "muted"}>{error ? `Cannot reach the API: ${error}` : "…"}</p>;
  }

  const canExport = analysis.measures.length > 0;

  return (
    <I18nProvider value={t}>
      <div className="layout">
        <header className="topbar">
          <h1>{t("app.title")}</h1>
          <div className="exports">
            <a className={`button ${canExport ? "" : "disabled"}`} href={api.exportUrl("excel", filters, analysis)}>
              {t("export.excel")}
            </a>
            <a className={`button ${canExport ? "" : "disabled"}`} href={api.exportUrl("pdf", filters, analysis)}>
              {t("export.pdf")}
            </a>
          </div>
        </header>

        <FiltersPanel onApply={setFilters} />

        <main>
          <nav className="tabs">
            <button className={tab === "data" ? "active" : ""} onClick={() => setTab("data")}>{t("tabs.data")}</button>
            <button className={tab === "analysis" ? "active" : ""} onClick={() => setTab("analysis")}>{t("tabs.analysis")}</button>
          </nav>

          {tab === "data" && <DataTable filters={filters} />}
          {tab === "analysis" && (
            <OlapPanel meta={meta} filters={filters} analysis={analysis} onChange={setAnalysis} />
          )}
        </main>
      </div>
    </I18nProvider>
  );
}
