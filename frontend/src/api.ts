export interface Filters {
  successful_tenderer?: string;
  contracting_authority?: string;
  location?: string;
  cpv?: string;
  amount_awarded_min?: string;
  amount_awarded_max?: string;
  downside_min?: string;
  downside_max?: string;
  publication_date_from?: string;
  publication_date_to?: string;
  award_date_from?: string;
  award_date_to?: string;
}

export interface Outcome {
  id: number;
  successful_tenderer: string | null;
  contracting_authority: string | null;
  location: string | null;
  amount_awarded: number | null;
  downside_amount: number | null;
  publication_date: string | null;
  award_date: string | null;
  cpv: string | null;
}

export interface OutcomePage {
  total: number;
  page: number;
  page_size: number;
  items: Outcome[];
}

export interface Option {
  key: string;
  label: string;
}

export interface Meta {
  dimensions: Option[];
  measures: Option[];
  stats: string[];
}

export type OlapRow = Record<string, string | number | null>;

export interface OlapResult {
  group_by: string[];
  measures: string[];
  rows: OlapRow[];
  totals: OlapRow;
}

export interface Analysis {
  groupBy: string[];
  measures: string[];
}

export function buildQuery(
  filters: Filters,
  extra: Record<string, string | number | string[]> = {},
): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.append(key, value);
  });
  Object.entries(extra).forEach(([key, value]) => {
    (Array.isArray(value) ? value : [value]).forEach((v) => params.append(key, String(v)));
  });
  return params.toString();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  meta: () => get<Meta>("/api/meta"),
  outcomes: (filters: Filters, page: number, pageSize: number, sortBy: string, sortDir: string) =>
    get<OutcomePage>(
      `/api/outcomes?${buildQuery(filters, { page, page_size: pageSize, sort_by: sortBy, sort_dir: sortDir })}`,
    ),
  olap: (filters: Filters, analysis: Analysis) =>
    get<OlapResult>(
      `/api/olap?${buildQuery(filters, { group_by: analysis.groupBy, measures: analysis.measures })}`,
    ),
  exportUrl: (format: "excel" | "pdf", filters: Filters, analysis: Analysis) =>
    `/api/export/${format}?${buildQuery(filters, { group_by: analysis.groupBy, measures: analysis.measures })}`,
};

const money = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" });
const percent = new Intl.NumberFormat("it-IT", { minimumFractionDigits: 3, maximumFractionDigits: 3 });

export const format = {
  money: (v: unknown) => (typeof v === "number" ? money.format(v) : ""),
  percent: (v: unknown) => (typeof v === "number" ? `${percent.format(v)}%` : ""),
  date: (v: unknown) => (typeof v === "string" ? new Date(v).toLocaleDateString("it-IT") : ""),
};
