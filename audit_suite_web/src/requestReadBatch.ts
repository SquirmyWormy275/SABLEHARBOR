import type { Engagement, Row } from "./api";
export type ReadOutcome = {
  id: string;
  status: "NOT_ATTEMPTED" | "SUCCEEDED" | "FAILED" | "AMBIGUOUS";
  message?: string;
};
export type ReadPlan = {
  engagementId: string;
  revision: number;
  mode: "SELECTED" | "FILTERED";
  selected: number;
  matched: number;
  eligible: string[];
  excluded: { id: string; reason: string }[];
  overLimit: boolean;
};
export type ReadEnvelope = {
  command_id: string;
  expected_revision: number;
  kind: "pbc.read";
  payload: { request_id: string };
};
export function requestReadAuthority(e: Engagement, viewer: string) {
  return JSON.stringify([
    viewer,
    e.id,
    e.scope,
    e.permissions,
    e.phase,
    e.company_source_binding,
    e.evidence_acquisition,
  ]);
}
export function matchingRequests(e: Engagement, query: string): Row[] {
  const text = query.trim().toLowerCase();
  return e.requests.filter((r) =>
    [r.id, r.title, r.status].some((v) =>
      String(v ?? "")
        .toLowerCase()
        .includes(text),
    ),
  );
}
export function planRequestReads(
  e: Engagement,
  query: string,
  selected: string[],
  mode: ReadPlan["mode"],
): ReadPlan {
  const matched = matchingRequests(e, query),
    matchedIds = new Set(matched.map((r) => r.id));
  const ids = [
    ...new Set(mode === "FILTERED" ? matched.map((r) => r.id) : selected),
  ];
  const eligible: string[] = [],
    excluded: ReadPlan["excluded"] = [];
  for (const id of ids) {
    const rows = e.requests.filter((r) => r.id === id);
    let reason = "";
    if (rows.length !== 1) reason = "Request missing or ambiguous";
    else if (!matchedIds.has(id)) reason = "Outside current filter";
    else if (
      rows[0].boundary_id &&
      !e.scope.boundaries.includes(String(rows[0].boundary_id))
    )
      reason = "Outside current boundary scope";
    else if (rows[0].unread !== true) reason = "No unread marker";
    if (reason) excluded.push({ id, reason });
    else eligible.push(id);
  }
  return {
    engagementId: e.id,
    revision: e.revision,
    mode,
    selected: ids.length,
    matched: matched.length,
    eligible,
    excluded,
    overLimit: ids.length > 20,
  };
}
export function acceptedReadResponse(
  e: Engagement,
  command: ReadEnvelope,
  response: Engagement,
) {
  const rows = response.requests.filter(
    (r) => r.id === command.payload.request_id,
  );
  return (
    response.id === e.id &&
    response.revision === command.expected_revision + 1 &&
    rows.length === 1 &&
    rows[0].unread === false
  );
}
