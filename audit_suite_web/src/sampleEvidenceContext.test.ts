import { it, expect } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import type { Engagement } from "./api";
import {
  sampleOriginalContext,
  sampleObservationReference,
} from "./sampleOriginalObservations";
import { SampleEvidenceContext } from "./SampleEvidenceContext";
function fixture() {
  const trace = {
    id: "X1",
    revision: 1,
    task_id: "T",
    task_digest: "t".repeat(64),
    workpaper_id: "W",
    workpaper_version: 1,
    workpaper_digest: "w".repeat(64),
    selection_id: "S",
    population_id: "P",
    population_status: "PROVISIONAL",
    actor: "RECORDER",
    recorded_at: "2027-01-02",
    items: [
      {
        item_id: "one",
        status: "OBSERVED",
        observation: "Earlier actual observation",
        selection_basis: "TARGETED",
        evidence: [
          { artifact_id: "A", sha256: "a".repeat(64), locator: "row1" },
        ],
      },
    ],
  };
  const e = {
    id: "E",
    revision: 3,
    permissions: ["learn"],
    artifacts: [{ id: "A", status: "AVAILABLE", sha256: "a".repeat(64) }],
    tasks: [{ id: "T" }],
    workpapers: [{ id: "W", versions: [{ version: 1 }, { version: 2 }] }],
    sample_executions: [
      trace,
      {
        ...trace,
        id: "X2",
        revision: 2,
        predecessor_id: "X1",
        items: [
          {
            ...trace.items[0],
            status: "EXCEPTION_RECORDED",
            observation: "Corrected observation",
          },
        ],
      },
    ],
    sample_execution_inputs: {
      engagement_id: "E",
      engagement_revision: 3,
      tasks: [{ task_id: "T", task_digest: trace.task_digest }],
      workpaper_versions: [
        {
          workpaper_id: "W",
          workpaper_version: 1,
          workpaper_digest: trace.workpaper_digest,
        },
      ],
    },
  } as unknown as Engagement;
  return { e, trace };
}
it("requires both exact artifact identity and SHA and preserves both revisions", () => {
  const { e, trace } = fixture();
  const rows = sampleOriginalContext(e, "A").rows;
  expect(rows).toHaveLength(2);
  expect(rows[0].observation).toBe("Earlier actual observation");
  expect(rows[0].successors).toEqual([
    { id: "X2", revision: 2, citesOriginal: true },
  ]);
  expect(rows[1].predecessorId).toBe("X1");
  trace.items[0].evidence[0].sha256 = "changed";
  expect(sampleOriginalContext(e, "A").rows).toHaveLength(0);
});
it("same SHA on another original never creates an association", () => {
  const { e } = fixture();
  e.artifacts.push({
    id: "OTHER",
    status: "AVAILABLE",
    sha256: "a".repeat(64),
  });
  expect(sampleOriginalContext(e, "OTHER").rows).toEqual([]);
});
it("correction that removes original leaves earlier citation and explicit successor relation", () => {
  const { e } = fixture();
  const t = e.sample_executions as Record<string, unknown>[];
  t[1] = { ...t[1], items: [] };
  const rows = sampleOriginalContext(e, "A").rows;
  expect(rows).toHaveLength(1);
  expect(rows[0].successors[0].citesOriginal).toBe(false);
});
it("historical navigation uses authoritative exact version pins, never latest", () => {
  const { e } = fixture();
  const r = sampleOriginalContext(e, "A").rows[0];
  expect(sampleObservationReference(e, r, "workpaper")).toEqual({
    collection: "workpapers",
    id: "W",
    version: 1,
  });
  expect(sampleObservationReference(e, r, "task")).toEqual({
    collection: "tasks",
    id: "T",
  });
  const pins = e.sample_execution_inputs as {
    tasks: unknown[];
    workpaper_versions: unknown[];
  };
  pins.tasks = [];
  pins.workpaper_versions = [
    {
      workpaper_id: "W",
      workpaper_version: 2,
      workpaper_digest: r.workpaperDigest,
    },
  ];
  expect(sampleObservationReference(e, r, "task")).toBeNull();
  expect(sampleObservationReference(e, r, "workpaper")).toBeNull();
  expect(sampleOriginalContext(e, "A").rows[0].workpaperVersion).toBe(1);
});
it("denies navigation on stale revision, replaced hash, duplicate identities or revoked permissions", () => {
  const { e } = fixture();
  const r = sampleOriginalContext(e, "A").rows[0];
  expect(
    sampleObservationReference({ ...e, revision: 4 }, r, "task"),
  ).toBeNull();
  expect(
    sampleObservationReference({ ...e, permissions: [] }, r, "workpaper"),
  ).toBeNull();
  expect(sampleOriginalContext({ ...e, permissions: [] }, "A").rows).toEqual(
    [],
  );
  e.artifacts[0].sha256 = "other";
  expect(sampleObservationReference(e, r, "workpaper")).toBeNull();
});
it("bounds ambiguous and oversized history without silently presenting complete coverage", () => {
  const { e, trace } = fixture();
  e.sample_executions = [trace, trace];
  expect(sampleOriginalContext(e, "A")).toEqual({
    rows: [],
    unavailable: true,
  });
  e.sample_executions = Array(10001).fill(trace);
  expect(sampleOriginalContext(e, "A")).toEqual({
    rows: [],
    unavailable: true,
  });
});
it("renders manual qualification and bounded10 rows without replacing history", () => {
  const { e, trace } = fixture();
  e.sample_executions = Array.from({ length: 12 }, (_, i) => ({
    ...trace,
    id: "X" + i,
  }));
  const html = renderToStaticMarkup(
    createElement(SampleEvidenceContext, {
      engagement: e,
      artifactId: "A",
      onOpen: () => {
        throw Error("No automatic navigation");
      },
    }),
  );
  expect(html.match(/<article/g)).toHaveLength(10);
  expect(html).toContain("12 matching observations");
  expect(html).toContain("not automatic passing results");
  expect(html).not.toContain("item_digest");
});
