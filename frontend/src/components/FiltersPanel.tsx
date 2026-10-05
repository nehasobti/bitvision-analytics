import { FormEvent, useState } from "react";
import type { Filters } from "../api";

interface Props {
  onApply: (filters: Filters) => void;
}

type Field = { key: keyof Filters; label: string; type: "text" | "number" | "date"; placeholder?: string };

const TEXT_FIELDS: Field[] = [
  { key: "successful_tenderer", label: "Successful tenderer", type: "text" },
  { key: "contracting_authority", label: "Contracting authority", type: "text" },
  { key: "location", label: "Location", type: "text" },
  { key: "cpv", label: "CPV (starts with)", type: "text", placeholder: "e.g. 4523" },
];

const RANGE_FIELDS: [string, Field, Field][] = [
  [
    "Amount awarded (€)",
    { key: "amount_awarded_min", label: "Min", type: "number" },
    { key: "amount_awarded_max", label: "Max", type: "number" },
  ],
  [
    "Downside (%)",
    { key: "downside_min", label: "Min", type: "number" },
    { key: "downside_max", label: "Max", type: "number" },
  ],
  [
    "Publication date",
    { key: "publication_date_from", label: "From", type: "date" },
    { key: "publication_date_to", label: "To", type: "date" },
  ],
  [
    "Award date",
    { key: "award_date_from", label: "From", type: "date" },
    { key: "award_date_to", label: "To", type: "date" },
  ],
];

export default function FiltersPanel({ onApply }: Props) {
  const [draft, setDraft] = useState<Filters>({});

  const input = (field: Field) => (
    <input
      type={field.type}
      step={field.type === "number" ? "any" : undefined}
      placeholder={field.placeholder ?? field.label}
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
      <h2>Filters</h2>
      {TEXT_FIELDS.map((field) => (
        <label key={field.key}>
          <span>{field.label}</span>
          {input(field)}
        </label>
      ))}
      {RANGE_FIELDS.map(([label, from, to]) => (
        <label key={label}>
          <span>{label}</span>
          <div className="range">
            {input(from)}
            {input(to)}
          </div>
        </label>
      ))}
      <div className="actions">
        <button type="submit" className="primary">Apply</button>
        <button type="button" onClick={reset}>Reset</button>
      </div>
    </form>
  );
}
