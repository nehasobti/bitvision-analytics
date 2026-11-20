import { FormEvent, KeyboardEvent, useEffect, useState } from "react";
import { api, budgetApi, format, type Azienda, type Budget as BudgetData, type BudgetKind, type BudgetLine, type BudgetTender } from "../api";
import { useT } from "../i18n";

const KINDS: BudgetKind[] = ["unit", "lump_sum", "percentage"];
const decimal = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 4 });
const EDIT_FORM = "budget-row-edit"; // the table row inputs belong to this form via their `form` attribute

// Values typed in the add form or in the row being edited (kept as strings while editing).
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
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);

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

  // After a failed change, reload so the page shows what is really saved.
  const failAndReload = (e: Error) => {
    if (tenderId !== null) budgetApi.get(tenderId).then(setBudget).catch(() => undefined);
    fail(e);
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
    }).catch(failAndReload);
  };

  // Moves the row at index `from` to index `to` (arrows and drag and drop).
  const move = (from: number, to: number) => {
    if (tenderId === null || !budget || from === to) return;
    const lines = [...budget.lines];
    const [moved] = lines.splice(from, 1);
    lines.splice(to, 0, moved);
    setBudget({ ...budget, lines }); // show the new order at once, the server answer confirms it
    budgetApi.reorder(tenderId, lines.map((l) => l.id)).then(show).catch(failAndReload);
  };

  const remove = (line: BudgetLine) => {
    if (tenderId === null || !window.confirm(t("budget.delete_confirm", { name: line.task }))) return;
    budgetApi.deleteLine(tenderId, line.id).then(show).catch(failAndReload);
  };

  const endDrag = () => {
    setDragIndex(null);
    setOverIndex(null);
  };

  // Line shown where the dragged row will land.
  const dropClass = (index: number) => {
    if (dragIndex === null || overIndex !== index || dragIndex === index) return "";
    return index < dragIndex ? "drop-before" : "drop-after";
  };

  const lines = budget?.lines ?? [];
  const editingId = draft?.id ?? null; // row edited in the table, if any
  const otherLines = lines.filter((l) => l.id !== editingId);

  const taskNames = (refs: number[]) =>
    refs.map((id) => lines.find((l) => l.id === id)?.task).filter(Boolean).join(", ");

  // Total shown while editing a row, before saving.
  const previewTotal = (d: Draft): number | null => {
    const qty = num(d.quantity);
    if (d.kind === "lump_sum") return num(d.total);
    if (d.kind === "unit") return qty !== null && num(d.unit_price) !== null ? qty * (num(d.unit_price) as number) : null;
    if (qty === null) return null;
    const base = lines.filter((l) => d.refs.includes(l.id)).reduce((sum, l) => sum + (l.total ?? 0), 0);
    return (base * qty) / 100;
  };

  const quantityCell = (line: BudgetLine) => {
    if (line.quantity === null) return "";
    return line.kind === "percentage" ? `${decimal.format(line.quantity)}%` : decimal.format(line.quantity);
  };

  const toggleRef = (d: Draft, id: number, checked: boolean) =>
    setDraft({ ...d, refs: checked ? [...d.refs, id] : d.refs.filter((r) => r !== id) });

  const refsPicker = (d: Draft) => (
    <div className="budget-refs-field">
      <span>{t("budget.select_tasks")}</span>
      <div className="budget-refs">
        {otherLines.length === 0 && <span className="muted">{t("budget.no_tasks")}</span>}
        {otherLines.map((l) => (
          <label key={l.id} className="check">
            <input type="checkbox" checked={d.refs.includes(l.id)} onChange={(e) => toggleRef(d, l.id, e.target.checked)} />
            {l.task} <span className="muted">({format.money(l.total)})</span>
          </label>
        ))}
      </div>
    </div>
  );

  const onEditKey = (e: KeyboardEvent) => {
    if (e.key === "Escape") setDraft(null);
  };

  // Inputs of the row being edited in the table.
  const editCells = (d: Draft) => {
    const set = (field: keyof Draft) => (e: { target: { value: string } }) => setDraft({ ...d, [field]: e.target.value });
    const cell = { form: EDIT_FORM, onKeyDown: onEditKey };
    return (
      <>
        <td>
          <input {...cell} required autoFocus value={d.task} onChange={set("task")} aria-label={t("budget.col_task")} />
        </td>
        <td className="num">
          {d.kind !== "lump_sum" && (
            <span className="cell-unit">
              <input {...cell} required type="number" min={0} step="any" value={d.quantity} onChange={set("quantity")}
                aria-label={d.kind === "percentage" ? t("budget.percent") : t("budget.col_quantity")} />
              {d.kind === "percentage" && "%"}
            </span>
          )}
        </td>
        <td className="num">
          {d.kind === "unit" && (
            <input {...cell} required type="number" min={0} step="any" value={d.unit_price} onChange={set("unit_price")} aria-label={t("budget.col_unit_price")} />
          )}
        </td>
        <td className="num">
          {d.kind === "lump_sum"
            ? <input {...cell} required type="number" step="any" value={d.total} onChange={set("total")} aria-label={t("budget.col_total")} />
            : format.money(previewTotal(d))}
        </td>
        <td>
          <input {...cell} value={d.note} onChange={set("note")} aria-label={t("budget.col_note")} />
        </td>
        <td className="row-actions">
          <button type="submit" form={EDIT_FORM} className="primary" disabled={d.kind === "percentage" && d.refs.length === 0}>
            {t("budget.save")}
          </button>
          <button type="button" onClick={() => setDraft(null)}>{t("budget.cancel")}</button>
        </td>
      </>
    );
  };

  const viewCells = (line: BudgetLine, index: number) => (
    <>
      <td>
        {line.task}
        {line.kind === "percentage" && (
          <span className="muted"> · {t("budget.percent_of", { pct: decimal.format(line.quantity ?? 0), tasks: taskNames(line.refs) || "—" })}</span>
        )}
      </td>
      <td className="num">{quantityCell(line)}</td>
      <td className="num">{line.unit_price === null ? "" : format.money(line.unit_price)}</td>
      <td className="num">{format.money(line.total)}</td>
      <td>{line.note}</td>
      <td className="row-actions">
        <button type="button" title={t("budget.move_up")} disabled={index === 0} onClick={() => move(index, index - 1)}>↑</button>
        <button type="button" title={t("budget.move_down")} disabled={index === lines.length - 1} onClick={() => move(index, index + 1)}>↓</button>
        <button type="button" onClick={() => setDraft(toDraft(line))}>{t("budget.edit")}</button>
        <button type="button" onClick={() => remove(line)}>{t("budget.delete")}</button>
      </td>
    </>
  );

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

          {draft && draft.id === null && (
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
              {draft.kind === "percentage" && refsPicker(draft)}
              <div className="actions">
                <button type="submit" className="primary" disabled={draft.kind === "percentage" && draft.refs.length === 0}>
                  {t("budget.add")}
                </button>
                <button type="button" onClick={() => setDraft(null)}>{t("budget.cancel")}</button>
              </div>
            </form>
          )}

          {/* Form of the row edited in the table; its inputs point here with form={EDIT_FORM}. */}
          <form id={EDIT_FORM} onSubmit={submit} hidden />

          <div className="table-scroll">
            <table className="mining-table budget-table">
              <thead>
                <tr>
                  <th />
                  <th>{t("budget.col_task")}</th>
                  <th className="num">{t("budget.col_quantity")}</th>
                  <th className="num">{t("budget.col_unit_price")}</th>
                  <th className="num">{t("budget.col_total")}</th>
                  <th>{t("budget.col_note")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {lines.map((line, index) => {
                  const editing = draft !== null && editingId === line.id;
                  return [
                    <tr
                      key={line.id}
                      draggable={editingId === null}
                      className={`${editing ? "editing" : ""} ${dragIndex === index ? "dragging" : ""} ${dropClass(index)}`}
                      title={editingId === null ? t("budget.dblclick_edit") : undefined}
                      onDoubleClick={() => { if (editingId === null) setDraft(toDraft(line)); }}
                      onDragStart={(e) => {
                        e.dataTransfer.effectAllowed = "move";
                        e.dataTransfer.setData("text/plain", String(line.id)); // required by Firefox
                        setDragIndex(index);
                      }}
                      onDragOver={(e) => {
                        if (dragIndex === null) return;
                        e.preventDefault();
                        e.dataTransfer.dropEffect = "move";
                        if (overIndex !== index) setOverIndex(index);
                      }}
                      onDrop={(e) => {
                        e.preventDefault();
                        if (dragIndex !== null) move(dragIndex, index);
                        endDrag();
                      }}
                      onDragEnd={endDrag}
                    >
                      <td className="drag-handle" title={t("budget.drag")}>⠿</td>
                      {editing ? editCells(draft) : viewCells(line, index)}
                    </tr>,
                    editing && draft.kind === "percentage" && (
                      <tr key={`${line.id}-refs`} className="editing">
                        <td />
                        <td colSpan={6}>{refsPicker(draft)}</td>
                      </tr>
                    ),
                  ];
                })}
                {lines.length === 0 && (
                  <tr><td colSpan={7} className="muted">{t("budget.empty")}</td></tr>
                )}
              </tbody>
              {lines.length > 0 && (
                <tfoot>
                  <tr>
                    <td colSpan={4}><strong>{t("budget.total")}</strong></td>
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
