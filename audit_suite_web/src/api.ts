export type Row = { id: string; [key: string]: unknown };
export type Capabilities = {
  custom_authoring?: boolean;
  experimental_review?: boolean;
  voice?: boolean;
  [key: string]: boolean | undefined;
};
export type Scope = {
  programs: string[];
  period_start: string;
  period_end: string;
  report_type: string;
  boundaries: string[];
  [key: string]: unknown;
};
export type Engagement = Row & {
  title: string;
  revision: number;
  discipline: string;
  mode: string;
  phase: string;
  scope: Scope;
  simulated_at: string;
  controls: Row[];
  people: Row[];
  tasks: Row[];
  requests: Row[];
  artifacts: Row[];
  meetings: Row[];
  notes: Row[];
  populations: Row[];
  selections: Row[];
  calendar: Row[];
  findings: Row[];
  workpapers: Row[];
  reviews: Row[];
  surveys: Row[];
  events: Row[];
  capabilities: Capabilities;
  generation?: {
    state: string;
    completed?: number;
    total?: number;
    stage?: string;
    errors?: string[];
  };
  permissions?: string[];
  trainer_encounter_counts?: {
    selector_id: string;
    option_id: string;
    basis: string;
    eligible: number;
    planned: number;
    excluded: number;
  }[];
};
export type Bootstrap = {
  viewer: { id: string; display_name: string; roles: string[] };
  csrf_token: string;
  engagements: Row[];
  capabilities: Capabilities;
  programs: Row[];
  people: Row[];
  controls: Row[];
  boundaries?: Row[];
  financial_accounts?: Row[];
  ism_catalog?: {
    requirements: Row[];
    version?: string;
    status?: string;
    reason?: string;
    attribution?: string;
    license?: string;
  };
  providers?: Record<string, Record<string, unknown>>;
};
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
let csrf = "";
export function setCSRF(value: string) {
  csrf = value;
}
export async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const isForm = body instanceof FormData;
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: {
      ...(method === "GET" ? {} : { "X-CSRF-Token": csrf }),
      ...(body && !isForm ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  });
  let result: Record<string, unknown> = {};
  try {
    result = await response.json();
  } catch {
    if (response.ok)
      throw new ApiError(
        "The service returned an unreadable response.",
        response.status,
      );
  }
  if (!response.ok)
    throw new ApiError(
      typeof result.error === "string"
        ? result.error
        : typeof result.detail === "string"
          ? result.detail
          : `Request failed (${response.status}).`,
      response.status,
    );
  return result as T;
}
export function command(
  id: string,
  revision: number,
  kind: string,
  payload: Record<string, unknown>,
) {
  return request<Engagement>(
    `/api/engagements/${encodeURIComponent(id)}/commands`,
    "POST",
    {
      command_id: crypto.randomUUID(),
      expected_revision: revision,
      kind,
      payload,
    },
  );
}
export function artifactURL(engagement: string, id: string) {
  return `/api/engagements/${encodeURIComponent(engagement)}/artifacts/${encodeURIComponent(id)}/download`;
}
export function str(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.map(str).join(", ");
  if (typeof value === "object") return "Linked record";
  return String(value);
}
export function human(value: unknown) {
  return str(value).replace(/_/g, " ").toLowerCase();
}
export const lists = [
  "controls",
  "people",
  "tasks",
  "requests",
  "artifacts",
  "meetings",
  "notes",
  "populations",
  "selections",
  "calendar",
  "findings",
  "workpapers",
  "reviews",
  "surveys",
  "events",
] as const;
export function normalize(e: Engagement): Engagement {
  for (const key of lists) if (!Array.isArray(e[key])) e[key] = [];
  e.capabilities ??= {};
  return e;
}

export async function requestAudio(
  path: string,
  body: Record<string, unknown>,
): Promise<Blob> {
  const response = await fetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let message = `Speech request failed (${response.status}).`;
    try {
      const data = await response.json();
      if (typeof data.error === "string") message = data.error;
    } catch {}
    throw new ApiError(message, response.status);
  }
  return response.blob();
}

export function workpaperVersions(row: Row): Row[] {
  return Array.isArray(row.versions)
    ? row.versions.map((v) => ({ ...v, id: `${row.id}:v${v.version}` }))
    : [];
}
export function canReviewWorkpaper(
  row: Row,
  viewerId: string | undefined,
  permissions: string[] = [],
  version?: Row,
): boolean {
  return Boolean(
    viewerId &&
    row.prepared_by !== viewerId &&
    version?.actor !== viewerId &&
    !workpaperVersions(row).some(
      (prior) =>
        Number(prior.version) <= Number(version?.version ?? 0) &&
        prior.actor === viewerId,
    ) &&
    permissions.some((p) => p === "review" || p === "instruct"),
  );
}
export function newWorkpaperVersion(row: Row): Record<string, unknown> {
  const latest: Record<string, unknown> = workpaperVersions(row).at(-1) ?? {};
  return {
    workpaper_id: row.id,
    text: latest.text ?? "",
    section: latest.section ?? "",
    objective: latest.objective ?? "",
    procedures: latest.procedures ?? "",
    conclusion: latest.conclusion ?? "",
    artifact_id: latest.artifact_id ?? "",
    evidence_ids: Array.isArray(latest.evidence_ids)
      ? latest.evidence_ids.join(", ")
      : "",
  };
}

export function requestHasDelivery(row: Row): boolean {
  return Array.isArray(row.artifact_ids) && row.artifact_ids.length > 0;
}
