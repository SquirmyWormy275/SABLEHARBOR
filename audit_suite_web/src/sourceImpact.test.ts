import { describe, it, expect } from "vitest";
import {
  impactContext,
  validateImpact,
  type ImpactReport,
} from "./sourceImpact";
import type { Engagement } from "./api";
const e = {
  id: "E",
  revision: 4,
  simulated_at: "2027-12-31",
  artifacts: [{ id: "A" }],
  scope: {},
  permissions: ["learn"],
} as Engagement;
const report = {
  engagement_id: "E",
  engagement_revision: 4,
  simulated_as_of: "2027-12-31",
  changes: [{ id: "x", artifact_id: "A", references: [] }],
  compared_artifacts: 2,
  unavailable_comparisons: 3,
  snapshot_isolation: "PER_SOURCE_OPERATION_NOT_GLOBAL",
  limitations: [],
  started_at: "2026-01-01",
  completed_at: "2026-01-01",
} as ImpactReport;
describe("source impact report pins", () => {
  it("keeps unavailable separate from successfully compared artifacts", () => {
    expect(validateImpact(report, e).unavailable_comparisons).toBe(3);
    expect(validateImpact(report, e).compared_artifacts).toBe(2);
  });
  it("rejects stale, wrong engagement or cutoff results", () => {
    for (const delta of [
      { engagement_id: "OTHER" },
      { engagement_revision: 3 },
      { simulated_as_of: "2026-01-01" },
    ])
      expect(() => validateImpact({ ...report, ...delta }, e)).toThrow(
        /outdated/,
      );
  });
  it("rejects invalid counts and out of workspace references", () => {
    expect(() =>
      validateImpact({ ...report, compared_artifacts: 0 }, e),
    ).toThrow();
    expect(() =>
      validateImpact({ ...report, unavailable_comparisons: -1 }, e),
    ).toThrow();
    expect(() =>
      validateImpact(
        {
          ...report,
          changes: [{ id: "x", artifact_id: "OTHER", references: [] }],
        },
        e,
      ),
    ).toThrow();
  });
  it("invalidates context on role, binding and acquisition changes even at same revision", () => {
    for (const delta of [
      { permissions: ["review"] },
      { company_source_binding: { branch: "other" } },
      { evidence_acquisition: { mode: "other" } },
    ])
      expect(impactContext({ ...e, ...delta } as Engagement)).not.toBe(
        impactContext(e),
      );
  });
});

import { impactReference, impactTraceLinks } from "./sourceImpact";
import type { Row } from "./api";
const hash = "a".repeat(64);
function linkedState() {
  const version = { version: 1, evidence_ids: ["A"], text: "Earlier text" };
  const anchor = {
    field: "text",
    start: 0,
    end: 7,
    excerpt: "Earlier",
    offset_unit: "UNICODE_CODEPOINT",
  };
  const trace = {
    id: "X",
    revision: 1,
    predecessor_id: null,
    task_id: "T",
    task_digest: hash,
    selection_id: "S",
    selection_digest: hash,
    population_id: "P",
    population_digest: hash,
    workpaper_id: "W",
    workpaper_version: 1,
    workpaper_digest: hash,
    items: [
      {
        item_id: "I",
        evidence: [{ artifact_id: "A", sha256: hash }],
        observation: "Earlier",
      },
    ],
  };
  return {
    ...e,
    artifacts: [{ id: "A", sha256: hash }],
    tasks: [{ id: "T" }],
    selections: [{ id: "S" }],
    populations: [{ id: "P", version: 1 }],
    workpapers: [
      {
        id: "W",
        versions: [version, { version: 2, evidence_ids: [], text: "Later" }],
      },
    ],
    reviews: [
      {
        id: "R",
        kind: "HUMAN",
        workpaper_id: "W",
        workpaper_version: 1,
        workpaper_version_digest: hash,
        anchor,
      },
    ],
    findings: [
      {
        id: "F",
        evidence_ids: [],
        remediations: [{ id: "M", evidence_ids: ["A"] }],
      },
    ],
    sample_executions: [trace],
    sample_execution_inputs: {
      status: "AVAILABLE",
      tasks: [{ task_id: "T", task_digest: hash }],
      selections: [
        {
          selection_id: "S",
          selection_digest: hash,
          population_id: "P",
          population_digest: hash,
          population_version: 1,
        },
      ],
      workpaper_versions: [
        { workpaper_id: "W", workpaper_version: 1, workpaper_digest: hash },
      ],
    },
  } as Engagement;
}
describe("typed impact navigation", () => {
  it("keeps the historical human review version and exact passage, not latest", () => {
    const state = linkedState(),
      row = state.reviews[0];
    const ref = {
      id: "R",
      collection: "reviews",
      workpaper_id: "W",
      version: 1,
      workpaper_version_digest: hash,
      anchor: row.anchor,
    };
    const target = impactReference(state, ref, "A")!;
    expect(target.workpaper?.version).toBe(1);
    expect(target.row.id).toBe("R");
    for (const changed of [
      { version: 2 },
      { workpaper_version_digest: "b".repeat(64) },
      { anchor: {} },
    ])
      expect(impactReference(state, { ...ref, ...changed }, "A")).toBeNull();
  });
  it("only opens exact trace revision/item/hash and correction predecessor", () => {
    const state = linkedState();
    const ref = {
      id: "X",
      collection: "sample_executions",
      version: 1,
      item_id: "I",
      artifact_sha256: hash,
      predecessor_id: null,
      successor_id: null,
    };
    expect(impactReference(state, ref, "A")?.item?.item_id).toBe("I");
    for (const changed of [
      { version: 2 },
      { item_id: "OTHER" },
      { artifact_sha256: "b".repeat(64) },
      { predecessor_id: "OTHER" },
      { successor_id: "OTHER" },
    ])
      expect(impactReference(state, { ...ref, ...changed }, "A")).toBeNull();
  });
  it("opens remediation evidence as remediation, never infers original finding support", () => {
    const state = linkedState();
    expect(
      impactReference(state, { id: "F", collection: "findings" }, "A"),
    ).toBeNull();
    expect(
      impactReference(
        state,
        { id: "F", collection: "findings", remediation_id: "M" },
        "A",
      )?.kind,
    ).toBe("finding");
    expect(
      impactReference(
        state,
        { id: "F", collection: "findings", remediation_id: "OTHER" },
        "A",
      ),
    ).toBeNull();
  });
  it("uses server digests for trace-related work and refuses replacement versions", () => {
    const state = linkedState(),
      trace = (state.sample_executions as Row[])[0];
    const links = impactTraceLinks(state, trace);
    expect(links).toHaveLength(4);
    expect(links.find((r) => r.collection === "workpapers")?.version).toBe(1);
    expect(
      impactTraceLinks(state, {
        ...trace,
        task_digest: "b".repeat(64),
        selection_digest: "b".repeat(64),
        workpaper_digest: "b".repeat(64),
      }),
    ).toEqual([]);
    expect(
      impactReference(
        state,
        { id: "W", collection: "workpapers", version: 3 },
        "A",
      ),
    ).toBeNull();
  });
  it("refuses duplicate identity and unavailable input projection", () => {
    const state = linkedState();
    state.workpapers.push({ ...state.workpapers[0] });
    expect(
      impactReference(
        state,
        { id: "W", collection: "workpapers", version: 1 },
        "A",
      ),
    ).toBeNull();
    state.sample_execution_inputs = { status: "INPUT_LIMIT_EXCEEDED" };
    expect(
      impactTraceLinks(state, (state.sample_executions as Row[])[0]),
    ).toEqual([]);
  });
});
