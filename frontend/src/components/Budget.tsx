import { FormEvent, useEffect, useState } from "react";
import { api, budgetApi, format, type Azienda, type Budget as BudgetData, type BudgetKind, type BudgetLine, type BudgetTender } from "../api";
import { useT } from "../i18n";

const KINDS: BudgetKind[] = ["unit", "lump_sum", "percentage"];
const decimal = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 4 });

// Values typed in the add/edit form (kept as strings while editing).
interface Draft {
  id: number | null; // null = new row
  kind: BudgetKind;
  task: string;
  quantity: string;
  unit_price: string;
  total: string;
  note: string;
  refs: number[];
}

const emptyDraft = (kind: BudgetKind): Draft => ({ id: null, kind, task: "", quantity: "", unit_price: "", total: "", note: "", refs: [] });

const toDraft = (line: BudgetLine): Draft => ({
  id: line.id,
  kind: line.kind,
  task: line.task,
  quantity: line.quantity?.toString() ?? "",
  unit_price: line.unit_price?.toString() ?? "",
  total: line.kind === "lump_sum" ? (line.total?.toString() ?? "") : "",
  note: line.note ?? "",
  refs: line.refs,
});

const num = (value: string) => (value.trim() === "" ? null : Number(value.replace(",", ".")));

// "Gestione budget": cost breakdown of a tender. Base d'asta comes from BitVision;
// Oneri sicurezza and the task rows are saved in this app.
export default function Budget() {
  const t = useT();
  const [aziende, setAziende] = useState<Azienda[]>([]);
  const [aziendaId, setAziendaId] = useState<number | null>(null);
  const [tenders, setTenders] = useState<BudgetTender[]>([]);
  const [tenderId, setTenderId] = useState<number | null>(null);
  const [budget, setBudget] = useState<BudgetData | null>(null);
  const [safety, setSafety] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fail = (e: Error) => setError(e.message);

  useEffect(() => {
    api.aziende().then((list) => {
      setAziende(list);
      if (list.length) setAziendaId(list[0].id);
    }).catch(fail);
  }, []);

  useEffect(() => {
    if (aziendaId === null) return;
    setTenders([]);
    setTenderId(null);
    budgetApi.tenders(aziendaId).then((list) => {
      setTenders(list);
      if (list.length) setTenderId(list[0].id);
    }).catch(fail);
  }, [aziendaId]);

  const show = (data: BudgetData) => {
    setBudget(data);
    setSafety(data.safety_costs?.toString() ?? "");
    setError(null);
  };

  useEffect(() => {
    setBudget(null);
    setDraft(null);
    if (tenderId !== null) budgetApi.get(tenderId).then(show).catch(fail);
  }, [tenderId]);

  const saveSafety = () => {
    if (tenderId === null || !budget) return;
    const value = num(safety);
    if (value === budget.safety_costs) return;
    budgetApi.setSafetyCosts(tenderId, value).then(show).catch(fail);
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (tenderId === null || !draft) return;
    const line = {
      kind: draft.kind,
      task: draft.task,
      quantity: num(draft.quantity),
      unit_price: num(draft.unit_price),
      total: num(draft.total),
      note: draft.note,
      refs: draft.refs,
    };
    const call = draft.id === null ? budgetApi.addLine(tenderId, line) : budgetApi.updateLine(tenderId, draft.id, line);
    call.then((data) => {
      show(data);
      setDraft(null);
    }).catch(fail);
  };

  const move = (index: number, step: -1 | 1) => {
    if (tenderId === null || !budget) return;
    const ids = budget.lines.map((l) => l.id);
    [ids[index], ids[index + step]] = [ids[index + step], ids[index]];
    budgetApi.reorder(tenderId, ids).then(show).catch(fail);
  };

  const remove = (line: BudgetLine) => {
    if (tenderId === null || !window.confirm(t("budget.delete_confirm", { name: line.task }))) return;
    budgetApi.deleteLine(tenderId, line.id).then(show).catch(fail);
  };

  const quantityCell = (line: BudgetLine) => {
    if (line.quantity === null) return "";
    return line.kind === "percentage"
      ? `${decimal.format(line.quantity)}%`
      : decimal.format(line.quantity);
  };

  const otherLines = budget?.lines.filter((l) => l.id !== draft?.id) ?? [];

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{t("budget.title")}</h2>
      </div>

      <div className="my-filters">
        <label>
          <span>{t("my.azienda")}</span>
          <select value={aziendaId ?? ""} onChange={(e) => setAziendaId(Number(e.target.value))}>
            {aziende.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </label>
        <label className="wide">
          <span>{t("budget.tender")}</span>
          <select value={tenderId ?? ""} onChange={(e) => setTenderId(Number(e.target.value))} disabled={!tenders.length}>
            {!tenders.length && <option value="">{t("budget.no_tenders")}</option>}
            {tenders.map((tender) => (
              <option key={tender.id} value={tender.id}>{[tender.cig, tender.title].filter(Boolean).join(" · ")}</option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="error">{error}</p>}

      {budget && (
        <>
          <div className="budget-head">
            <div className="tile">
              <span className="tile-label">{t("budget.base_amount")}</span>
              <strong className="tile-value">{format.money(budget.tender.base_amount) || "—"}</strong>
            </div>
            <label className="tile">
              <span className="tile-label">{t("budget.safety_costs")} (€)</span>
              <input type="number" min={0} step="0.01" value={safety} onChange={(e) => setSafety(e.target.value)} onBlur={saveSafety} />
            </label>
          </div>

          <div className="actions budget-add">
            {KINDS.map((kind) => (
              <button key={kind} type="button" className="primary" onClick={() => setDraft(emptyDraft(kind))}>
                + {t(`budget.${kind}`)}
              </button>
            ))}
          </div>

          {draft && (
            <form className="budget-form" onSubmit={submit}>
              <strong>{t(`budget.${draft.kind}`)}</strong>
              <label className="wide">
                <span>{t("budget.col_task")}</span>
                <input required autoFocus value={draft.task} onChange={(e) => setDraft({ ...draft, task: e.target.value })} />
              </label>
              {draft.kind !== "lump_sum" && (
                <label>
                  <span>{draft.kind === "percentage" ? t("budget.percent") : t("budget.col_quantity")}</span>
                  <input required type="number" min={0} step="any" value={draft.quantity} onChange={(e) => setDraft({ ...draft, quantity: e.target.value })} />
                </label>
              )}
              {draft.kind === "unit" && (
                <label>
                  <span>{t("budget.col_unit_price")}</span>
                  <input required type="number" min={0} step="any" value={draft.unit_price} onChange={(e) => setDraft({ ...draft, unit_price: e.target.value })} />
                </label>
              )}
              {draft.kind === "lump_sum" && (
                <label>
                  <span>{t("budget.col_total")}</span>
                  <input required type="number" step="any" value={draft.total} onChange={(e) => setDraft({ ...draft, total: e.target.value })} />
                </label>
              )}
              <label className="wide">
                <span>{t("budget.col_note")}</span>
                <input value={draft.note} onChange={(e) => setDraft({ ...draft, note: e.target.value })} />
              </label>
              {draft.kind === "percentage" && (
                <fieldset className="budget-refs">
                  <legend>{t("budget.select_tasks")}</legend>
                  {otherLines.length === 0 && <span className="muted">{t("budget.no_tasks")}</span>}
                  {otherLines.map((l) => (
                    <label key={l.id} className="check">
                      <input
                        type="checkbox"
                        checked={draft.refs.includes(l.id)}
                        onChange={(e) => setDraft({ ...draft, refs: e.target.checked ? [...draft.refs, l.id] : draft.refs.filter((r) => r !== l.id) })}
                      />
                      {l.task} <span className="muted">({format.money(l.total)})</span>
                    </label>
                  ))}
                </fieldset>
              )}
              <div className="actions">
                <button type="submit" className="primary" disabled={draft.kind === "percentage" && draft.refs.length === 0}>
                  {draft.id === null ? t("budget.add") : t("budget.save")}
                </button>
                <button type="button" onClick={() => setDraft(null)}>{t("budget.cancel")}</button>
              </div>
            </form>
          )}

          <div className="table-scroll">
            <table className="mining-table budget-table">
              <thead>
                <tr>
                  <th>{t("budget.col_task")}</th>
                  <th className="num">{t("budget.col_quantity")}</th>
                  <th className="num">{t("budget.col_unit_price")}</th>
                  <th className="num">{t("budget.col_total")}</th>
                  <th>{t("budget.col_note")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {budget.lines.map((line, index) => (
                  <tr key={line.id}>
                    <td>
                      {line.task}
                      {line.kind === "percentage" && (
                        <span className="muted"> · {t("budget.percent_of", { pct: decimal.format(line.quantity ?? 0), count: line.refs.length })}</span>
                      )}
                    </td>
                    <td className="num">{quantityCell(line)}</td>
                    <td className="num">{line.unit_price === null ? "" : format.money(line.unit_price)}</td>
                    <td className="num">{format.money(line.total)}</td>
                    <td>{line.note}</td>
                    <td className="row-actions">
                      <button type="button" title={t("budget.move_up")} disabled={index === 0} onClick={() => move(index, -1)}>↑</button>
                      <button type="button" title={t("budget.move_down")} disabled={index === budget.lines.length - 1} onClick={() => move(index, 1)}>↓</button>
                      <button type="button" onClick={() => setDraft(toDraft(line))}>{t("budget.edit")}</button>
                      <button type="button" onClick={() => remove(line)}>{t("budget.delete")}</button>
                    </td>
                  </tr>
                ))}
                {budget.lines.length === 0 && (
                  <tr><td colSpan={6} className="muted">{t("budget.empty")}</td></tr>
                )}
              </tbody>
              {budget.lines.length > 0 && (
                <tfoot>
                  <tr>
                    <td colSpan={3}><strong>{t("budget.total")}</strong></td>
                    <td className="num"><strong>{format.money(budget.lines_total)}</strong></td>
                    <td colSpan={2} />
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </>
      )}
    </section>
  );
}
