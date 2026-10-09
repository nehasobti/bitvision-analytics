import { FormEvent, useEffect, useState } from "react";
import { api, type Analysis, type Filters, type SavedView } from "../api";
import { useT } from "../i18n";

interface Props {
  filters: Filters;
  analysis: Analysis;
  onLoad: (view: SavedView) => void;
}

const activeFilters = (filters: Filters) =>
  JSON.stringify(Object.entries(filters).filter(([, v]) => v !== undefined && v !== "").sort());

function matches(view: SavedView, filters: Filters, analysis: Analysis): boolean {
  return (
    activeFilters(view.filters) === activeFilters(filters) &&
    view.group_by.join() === analysis.groupBy.join() &&
    view.measures.join() === analysis.measures.join()
  );
}

// Save the applied filters + Raggruppa per + Misure under a description, and apply them again later.
export default function SavedViews({ filters, analysis, onLoad }: Props) {
  const t = useT();
  const [views, setViews] = useState<SavedView[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = () =>
    api
      .savedViews()
      .then(setViews)
      .catch((e: Error) => setError(e.message));

  useEffect(() => {
    refresh();
  }, []);

  // Once filters or grouping change, the selected analysis is no longer the one applied.
  useEffect(() => {
    const view = views.find((v) => v.id === selectedId);
    if (view && !matches(view, filters, analysis)) setSelectedId(null);
  }, [filters, analysis]);

  const choose = (id: string) => {
    const view = views.find((v) => v.id === Number(id));
    setSelectedId(view ? view.id : null);
    if (view) onLoad(view);
  };

  const save = (e: FormEvent) => {
    e.preventDefault();
    api
      .saveView(description.trim(), filters, analysis)
      .then((view) => {
        setSaving(false);
        setDescription("");
        setSelectedId(view.id);
        setError(null);
        return refresh();
      })
      .catch((e: Error) => setError(e.message));
  };

  const remove = () => {
    const view = views.find((v) => v.id === selectedId);
    if (!view || !window.confirm(t("saved.delete_confirm", { name: view.description }))) return;
    api
      .deleteView(view.id)
      .then(() => {
        setSelectedId(null);
        return refresh();
      })
      .catch((e: Error) => setError(e.message));
  };

  return (
    <div className="saved-views">
      {saving ? (
        <form className="saved-form" onSubmit={save}>
          <input
            autoFocus
            maxLength={255}
            placeholder={t("saved.description")}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <button type="submit" className="primary" disabled={!description.trim() || analysis.measures.length === 0}>
            {t("saved.confirm")}
          </button>
          <button type="button" onClick={() => setSaving(false)}>{t("saved.cancel")}</button>
        </form>
      ) : (
        <>
          <select value={selectedId ?? ""} onChange={(e) => choose(e.target.value)}>
            <option value="">{t("saved.choose")}</option>
            {views.map((v) => (
              <option key={v.id} value={v.id}>{v.description}</option>
            ))}
          </select>
          {selectedId !== null && (
            <button type="button" onClick={remove}>{t("saved.delete")}</button>
          )}
          <button type="button" className="primary" title={t("saved.hint")} onClick={() => setSaving(true)}>
            {t("saved.save")}
          </button>
        </>
      )}
      {error && <span className="error">{error}</span>}
    </div>
  );
}
