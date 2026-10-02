/** Volatile user-authored drafts only. No browser storage, model call or auto-submit. */
export type DraftKind = "workpaper.update" | "workpaper.add" | "note.create";
export const WORKPAPER_DRAFT_BYTES = 8 * 1024 * 1024;
export type DraftKey = {
  actorId: string;
  engagementId: string;
  kind: DraftKind;
  objectId: string;
  baseVersion: string;
};
export type DraftValues = Record<string, string | number | boolean | string[]>;
export type Draft = {
  key: DraftKey;
  values: DraftValues;
  sequence: number;
  sourceBasis: string;
};
export type DraftLookup =
  | { status: "EMPTY" }
  | { status: "CURRENT" | "STALE_BASE" | "STALE_SOURCE"; draft: Draft };
export type DraftScope = {
  actorId: string;
  engagementId: string;
  roles: string[];
  permissions: string[];
  scope: unknown;
  companySourceBinding: unknown;
  evidenceAcquisition: unknown;
};
/** These choices must be made again against the newly authorized source context. */
export const sourceLinkedDraftFields = [
  "evidence_ids",
  "artifact_id",
  "task_ids",
  "control_id",
  "source_message_id",
  "meeting_id",
  "person_id",
] as const;
export const draftSourceBasis = (binding: unknown, acquisition: unknown) =>
  JSON.stringify([binding, acquisition]);
export function withoutSourceLinks<T extends Record<string, unknown>>(
  values: T,
): T {
  const retained = { ...values };
  for (const field of sourceLinkedDraftFields) delete retained[field];
  return retained;
}
const allowed: Record<DraftKind, readonly string[]> = {
  "workpaper.add": [
    "title",
    "section",
    "code",
    "control_id",
    "objective",
    "procedures",
    "text",
    "artifact_id",
    "evidence_ids",
    "task_ids",
    "conclusion",
  ],
  "workpaper.update": [
    "section",
    "objective",
    "procedures",
    "text",
    "artifact_id",
    "evidence_ids",
    "task_ids",
    "conclusion",
  ],
  "note.create": [
    "title",
    "text",
    "control_id",
    "meeting_id",
    "person_id",
    "source_message_id",
  ],
};
const keyId = (key: DraftKey) =>
  JSON.stringify([
    key.actorId,
    key.engagementId,
    key.kind,
    key.objectId,
    key.baseVersion,
  ]);
const sameObject = (a: DraftKey, b: DraftKey) =>
  a.actorId === b.actorId &&
  a.engagementId === b.engagementId &&
  a.kind === b.kind &&
  a.objectId === b.objectId;
const clone = (draft: Draft): Draft => ({
  key: { ...draft.key },
  values: structuredClone(draft.values),
  sequence: draft.sequence,
  sourceBasis: draft.sourceBasis,
});
export function createDraftStore() {
  let active: DraftScope | null = null,
    identity = "",
    sourceBasis = "",
    sequence = 0;
  const entries = new Map<string, Draft>();
  function check(key: DraftKey) {
    if (
      !active ||
      active.actorId !== key.actorId ||
      active.engagementId !== key.engagementId ||
      !["learn", "instruct"].some((p) => active!.permissions.includes(p))
    )
      throw Error("Draft context is not authorized.");
    if (!Object.hasOwn(allowed, key.kind) || !key.objectId || !key.baseVersion)
      throw Error("Invalid draft identity.");
  }
  function put(
    key: DraftKey,
    values: Record<string, unknown>,
    reviewedSource = false,
  ) {
    check(key);
    const prior = entries.get(keyId(key));
    if (prior && prior.sourceBasis !== sourceBasis && !reviewedSource)
      throw Error(
        "Draft source context changed; review current sources and reselect linked records.",
      );
    const projected: DraftValues = {};
    for (const field of allowed[key.kind]) {
      const value = values[field];
      if (value === undefined) continue;
      if (
        field === "task_ids" &&
        Array.isArray(value) &&
        value.length <= 500 &&
        value.every(
          (id) => typeof id === "string" && id.length > 0 && id.length <= 128,
        ) &&
        new Set(value).size === value.length
      ) {
        projected[field] = [...value];
        continue;
      }
      if (
        typeof value !== "string" &&
        typeof value !== "boolean" &&
        typeof value !== "number"
      )
        throw Error("Draft fields must be plain form values.");
      if (typeof value === "number" && !Number.isFinite(value))
        throw Error("Invalid numeric draft field.");
      projected[field] = value;
    }
    const serialized = JSON.stringify(projected);
    const oversize =
      key.kind === "note.create"
        ? serialized.length > 100_000
        : new TextEncoder().encode(serialized).byteLength >
          WORKPAPER_DRAFT_BYTES;
    if (oversize)
      throw Error(
        "Draft exceeds the in-memory size limit. Keep the form open and save or shorten it.",
      );
    const id = keyId(key);
    if (!entries.has(id) && entries.size >= 32)
      throw Error(
        "Draft limit reached. Save or explicitly discard an existing draft.",
      );
    const next = {
      key: { ...key },
      values: projected,
      sequence: ++sequence,
      sourceBasis,
    };
    entries.set(id, next);
    return clone(next);
  }
  return {
    activate(scope: DraftScope) {
      const next = JSON.stringify([
        scope.actorId,
        scope.engagementId,
        [...scope.roles].sort(),
        [...scope.permissions].sort(),
        scope.scope,
      ]);
      if (next !== identity) {
        entries.clear();
        identity = next;
      }
      sourceBasis = draftSourceBasis(
        scope.companySourceBinding,
        scope.evidenceAcquisition,
      );
      active = {
        ...scope,
        roles: [...scope.roles],
        permissions: [...scope.permissions],
      };
    },
    save: put,
    lookup(key: DraftKey): DraftLookup {
      check(key);
      const exact = entries.get(keyId(key));
      if (exact)
        return {
          status:
            exact.sourceBasis === sourceBasis ? "CURRENT" : "STALE_SOURCE",
          draft: clone(exact),
        };
      const older = [...entries.values()]
        .filter((e) => sameObject(e.key, key))
        .sort((a, b) => b.sequence - a.sequence)[0];
      return older
        ? {
            status:
              older.sourceBasis === sourceBasis ? "STALE_BASE" : "STALE_SOURCE",
            draft: clone(older),
          }
        : { status: "EMPTY" };
    },
    /** Call only after an explicit user decision to use old draft text against the inspected current base. */
    rebase(previous: DraftKey, current: DraftKey) {
      check(previous);
      check(current);
      if (!sameObject(previous, current))
        throw Error("Cannot move a draft across objects.");
      const draft = entries.get(keyId(previous));
      if (!draft) throw Error("Draft no longer exists.");
      if (draft.sourceBasis !== sourceBasis)
        throw Error(
          "Draft source context changed; review current sources first.",
        );
      return put(current, draft.values);
    },
    /** Explicitly retain authored text while dropping all old source selections. */
    reviewSource(key: DraftKey) {
      check(key);
      const found = this.lookup(key);
      if (found.status !== "STALE_SOURCE")
        throw Error("No stale source draft to review.");
      return put(key, withoutSourceLinks(found.draft.values), true);
    },
    discard(key: DraftKey) {
      check(key);
      entries.delete(keyId(key));
    },
    /** Use after successful explicit save, or an explicit discard-all decision for this object. */
    discardObject(key: DraftKey) {
      check(key);
      for (const [id, draft] of entries)
        if (sameObject(draft.key, key)) entries.delete(id);
    },
    clear() {
      entries.clear();
      active = null;
      identity = "";
      sourceBasis = "";
    },
  };
}
export type DraftStore = ReturnType<typeof createDraftStore>;
