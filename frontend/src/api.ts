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
  language: string;
  messages: Record<string, string>;
  dimensions: Option[];
  measures: Option[];
  stats: string[];
  tender_statuses: string[];
}

// "Le mie gare": tenders the company took part in, our ribasso vs the winner's.
export type TenderResult = "won" | "lost" | "not_ranked" | "no_outcome";

export interface MyTendersFilters {
  azienda_id?: number;
  q?: string;
  status?: string; // one tender status, or "concluded"
  result?: TenderResult;
  deadline_from?: string;
  deadline_to?: string;
}

export interface MyTenderRow {
  tender_id: number;
  title: string;
  cig: string | null;
  contracting_authority: string | null;
  status: string | null;
  submission_deadline: string | null;
  base_amount: number | null;
  participants_count: number;
  our_position: number | null;
  our_downside: number | null;
  winner: string | null;
  winner_downside: number | null;
  difference: number | null;
  result: TenderResult;
}

export interface MyTendersSummary {
  tenders: number;
  with_outcome: number;
  won: number;
  lost: number;
  not_ranked: number;
  difference_avg: number | null;
  difference_min: number | null;
  difference_max: number | null;
}

export interface Azienda {
  id: number;
  name: string;
}

function myTendersQuery(f: MyTendersFilters): string {
  const params = new URLSearchParams();
  Object.entries(f).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.append(key, String(value));
  });
  return params.toString();
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

export interface SavedView {
  id: number;
  description: string;
  filters: Filters;
  group_by: string[];
  measures: string[];
  created_at: string;
}

export interface MiningSettings {
  outlier_k: number;
  min_wins: number;
  min_share: number;
  repeat_tolerance: number;
  min_repeats: number;
  max_stdev: number;
}

export type MiningKind = "money" | "percent" | "date" | "int" | "number" | "text" | "list" | "direction";

export interface MiningSection {
  key: string;
  title: string;
  hint: string;
  columns: [string, string, MiningKind][];
  rows: Record<string, unknown>[];
}

export interface MiningReport {
  records: number;
  settings: MiningSettings;
  sections: MiningSection[];
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const get = <T,>(path: string) => request<T>(path);

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
  savedViews: () => get<SavedView[]>("/api/saved-views"),
  saveView: (description: string, filters: Filters, analysis: Analysis) =>
    request<SavedView>("/api/saved-views", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        description,
        filters: Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined && v !== "")),
        group_by: analysis.groupBy,
        measures: analysis.measures,
      }),
    }),
  deleteView: (id: number) => request<void>(`/api/saved-views/${id}`, { method: "DELETE" }),
  mining: (filters: Filters, settings: MiningSettings) =>
    get<MiningReport>(`/api/mining?${buildQuery(filters, { ...settings })}`),
  miningExportUrl: (format: "excel" | "pdf", filters: Filters, settings: MiningSettings) =>
    `/api/mining/export/${format}?${buildQuery(filters, { ...settings })}`,
  aziende: () => get<Azienda[]>("/api/my-tenders/aziende"),
  myTenders: (f: MyTendersFilters) =>
    get<{ rows: MyTenderRow[]; summary: MyTendersSummary }>(`/api/my-tenders?${myTendersQuery(f)}`),
  myTendersExportUrl: (format: "excel" | "pdf", f: MyTendersFilters) =>
    `/api/my-tenders/export/${format}?${myTendersQuery(f)}`,
};

const money = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" });
const percent = new Intl.NumberFormat("it-IT", { minimumFractionDigits: 3, maximumFractionDigits: 3 });

export const format = {
  money: (v: unknown) => (typeof v === "number" ? money.format(v) : ""),
  percent: (v: unknown) => (typeof v === "number" ? `${percent.format(v)}%` : ""),
  date: (v: unknown) => (typeof v === "string" ? new Date(v).toLocaleDateString("it-IT") : ""),
  // Signed difference in percentage points, e.g. "-3,300".
  points: (v: unknown) => (typeof v === "number" ? `${v > 0 ? "+" : ""}${percent.format(v)}` : ""),
};
