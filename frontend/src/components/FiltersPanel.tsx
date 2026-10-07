import { FormEvent, useState } from "react";
import type { Filters } from "../api";
import { useT } from "../i18n";

interface Props {
  onApply: (filters: Filters) => void;
}

// label/placeholder are i18n keys.
type Field = { key: keyof Filters; label: string; type: "text" | "number" | "date"; placeholder?: string };

const TEXT_FIELDS: Field[] = [
  { key: "successful_tenderer", label: "fields.successful_tenderer", type: "text" },
  { key: "contracting_authority", label: "fields.contracting_authority", type: "text" },
  { key: "location", label: "fields.location", type: "text" },
  { key: "cpv", label: "fields.cpv", type: "text", placeholder: "filters.cpv_placeholder" },
];

const RANGE_FIELDS: [string, Field, Field][] = [
  [
    "fields.amount_awarded",
    { key: "amount_awarded_min", label: "filters.min", type: "number" },
    { key: "amount_awarded_max", label: "filters.max", type: "number" },
  ],
  [
    "fields.downside_amount",
    { key: "downside_min", label: "filters.min", type: "number" },
    { key: "downside_max", label: "filters.max", type: "number" },
  ],
  [
    "fields.publication_date",
    { key: "publication_date_from", label: "filters.from", type: "date" },
    { key: "publication_date_to", label: "filters.to", type: "date" },
  ],
  [
    "fields.award_date",
    { key: "award_date_from", label: "filters.from", type: "date" },
    { key: "award_date_to", label: "filters.to", type: "date" },
  ],
];

export default function FiltersPanel({ onApply }: Props) {
  const t = useT();
  const [draft, setDraft] = useState<Filters>({});

  const input = (field: Field) => (
    <input
      type={field.type}
      step={field.type === "number" ? "any" : undefined}
      placeholder={t(field.placeholder ?? field.label)}
      value={draft[field.key] ?? ""}
      onChange={(e) => setDraft({ ...draft, [field.key]: e.target.value })}
    />
  );

  const submit = (e: FormEvent) => {
    e.preventDefault();
    onApply(draft);
  };

  const reset = () => {
    setDraft({});
    onApply({});
  };

  return (
    <form className="panel filters" onSubmit={submit}>
      <h2>{t("filters.title")}</h2>
      {TEXT_FIELDS.map((field) => (
        <label key={field.key}>
          <span>
            {t(field.label)}
            {field.key === "cpv" && ` (${t("filters.starts_with")})`}
          </span>
          {input(field)}
        </label>
      ))}
      {RANGE_FIELDS.map(([label, from, to]) => (
        <label key={label}>
          <span>{t(label)}</span>
          <div className="range">
            {input(from)}
            {input(to)}
          </div>
        </label>
      ))}
      <div className="actions">
        <button type="submit" className="primary">{t("filters.apply")}</button>
        <button type="button" onClick={reset}>{t("filters.reset")}</button>
      </div>
    </form>
  );
}
