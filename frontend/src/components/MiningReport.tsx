import { useEffect, useRef, useState } from "react";
import { api, format, type Filters, type MiningKind, type MiningReport as Report, type MiningSettings } from "../api";
import { useT, type Translate } from "../i18n";

interface Props {
  filters: Filters;
  onClose: () => void;
}

// Same defaults as MiningSettings in backend/app/services/mining.py.
const DEFAULTS: MiningSettings = {
  outlier_k: 1.5,
  min_wins: 3,
  min_share: 30,
  repeat_tolerance: 0,
  min_repeats: 3,
  max_stdev: 0.5,
};

const SETTING_INPUTS: { key: keyof MiningSettings; step: number; min: number; max: number }[] = [
  { key: "outlier_k", step: 0.1, min: 0.5, max: 10 },
  { key: "min_wins", step: 1, min: 2, max: 1000 },
  { key: "min_share", step: 1, min: 1, max: 100 },
  { key: "repeat_tolerance", step: 0.001, min: 0, max: 5 },
  { key: "min_repeats", step: 1, min: 2, max: 1000 },
  { key: "max_stdev", step: 0.1, min: 0, max: 50 },
];

const NUMERIC: MiningKind[] = ["money", "percent", "int", "number"];
const decimal = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 2 });

function cell(value: unknown, kind: MiningKind, t: Translate): string {
  if (value === null || value === undefined) return "";
  switch (kind) {
    case "money": return format.money(value);
    case "percent": return format.percent(value);
    case "date": return format.date(value);
    case "number": return typeof value === "number" ? decimal.format(value) : "";
    case "list": return (value as string[]).join(", ");
    case "direction": return t(`mining.${value}`);
    default: return String(value);
  }
}

// Data mining report on the filtered data, with thresholds the user can adjust.
export default function MiningReport({ filters, onClose }: Props) {
  const t = useT();
  const [settings, setSettings] = useState<MiningSettings>(DEFAULTS);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Recalculate shortly after the user stops editing a threshold.
  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(true);
      api
        .mining(filters, settings)
        .then((res) => {
          setReport(res);
          setError(null);
        })
        .catch((e: Error) => setError(e.message))
        .finally(() => setLoading(false));
    }, 400);
    return () => clearTimeout(timer);
  }, [filters, settings]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Only send values in range: while typing "0.5" the field briefly holds "0", which the API rejects.
  // Out-of-range fields are shown in red (:out-of-range) until corrected.
  const update = (input: HTMLInputElement, key: keyof MiningSettings) => {
    const { badInput, rangeUnderflow, rangeOverflow } = input.validity;
    if (input.value === "" || badInput || rangeUnderflow || rangeOverflow) return;
    setSettings({ ...settings, [key]: Number(input.value) });
  };

  // Close only on a real click on the backdrop: selecting text in an input and releasing
  // the mouse outside the dialog also fires a click on the backdrop.
  const pressedOnBackdrop = useRef(false);

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => (pressedOnBackdrop.current = e.target === e.currentTarget)}
      onClick={(e) => {
        if (pressedOnBackdrop.current && e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal panel" role="dialog" aria-modal="true">
        <div className="panel-header">
          <div>
            <h2>{t("mining.title")}</h2>
            <span className="muted">
              {loading ? t("app.loading") : report && t("mining.records", { count: report.records })}
            </span>
          </div>
          <div className="exports">
            <a className="button" href={api.miningExportUrl("excel", filters, settings)}>{t("export.excel")}</a>
            <a className="button" href={api.miningExportUrl("pdf", filters, settings)}>{t("export.pdf")}</a>
            <button type="button" onClick={onClose}>{t("mining.close")}</button>
          </div>
        </div>

        <fieldset className="mining-settings">
          <legend>{t("mining.settings")}</legend>
          {SETTING_INPUTS.map((s) => (
            <label key={s.key}>
              <span>{t(`mining.${s.key}`)}</span>
              <input
                type="number"
                step={s.step}
                min={s.min}
                max={s.max}
                defaultValue={DEFAULTS[s.key]}
                onChange={(e) => update(e.target, s.key)}
              />
            </label>
          ))}
        </fieldset>

        {error && <p className="error">{error}</p>}

        {report?.sections.map((section) => (
          <section key={section.key} className="mining-section">
            <h3>
              {section.title} <span className="count">{section.rows.length}</span>
            </h3>
            {section.hint && <p className="muted">{section.hint}</p>}
            {section.rows.length === 0 ? (
              <p className="muted">{t("mining.none")}</p>
            ) : (
              <div className="table-scroll">
                <table className="mining-table">
                  <thead>
                    <tr>
                      {section.columns.map(([key, label, kind]) => (
                        <th key={key} className={NUMERIC.includes(kind) ? "num" : ""}>{label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {section.rows.map((row, i) => (
                      <tr key={i}>
                        {section.columns.map(([key, , kind]) => (
                          <td key={key} className={`${NUMERIC.includes(kind) ? "num" : ""} ${kind === "direction" ? `dir-${row[key]}` : ""}`}>
                            {cell(row[key], kind, t)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
