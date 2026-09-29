import { it, expect } from "vitest";
import type { Engagement } from "./api";
import {
  inputPins,
  executionPayload,
  type Pins,
  type Draft,
  selectionItems,
} from "./sampleExecution";
export function fixture() {
  const p: Pins = {
    engagement_id: "E",
    engagement_revision: 2,
    status: "AVAILABLE",
    tasks: [
      {
        task_id: "T",
        task_digest: "t-server",
        control_id: "C",
        boundary_id: "B",
      },
    ],
    selections: [
      {
        selection_id: "S",
        selection_digest: "s-server",
        population_id: "P",
        population_digest: "p-server",
        boundary_id: "B",
        sampling_unit: "row",
        population_status: "PROVISIONAL",
        selection_provisional: true,
      },
    ],
    workpaper_versions: [
      {
        workpaper_id: "W",
        workpaper_version: 1,
        workpaper_digest: "w-server",
        task_ids: ["T"],
      },
    ],
    artifacts: [{ artifact_id: "A", sha256: "a-server", bytes: 1 }],
    correctable_executions: [],
  };
  const e = {
    id: "E",
    revision: 2,
    permissions: ["learn"],
    sample_execution_inputs: p,
    selections: [
      { id: "S", immutable: { selected_ids: ["one"], targeted_ids: ["two"] } },
    ],
    sample_executions: [],
  } as unknown as Engagement;
  const d: Draft = {
    task: "T",
    selection: "S",
    workpaper: "W:1",
    purpose: "purpose",
    procedure: "procedure",
    rationale: "",
    items: [
      {
        item_id: "one",
        status: "OBSERVED",
        observation: "actual observation",
        evidence: [{ artifact_id: "A", sha256: "a-server", locator: "row1" }],
      },
    ],
  };
  return { e, p, d };
}
it("forwards authoritative pins and historical version without recomputing numbers", () => {
  const { e, p, d } = fixture();
  expect(executionPayload(e, p, d)).toMatchObject({
    task_digest: "t-server",
    population_digest: "p-server",
    workpaper_version: 1,
    workpaper_digest: "w-server",
  });
  expect(selectionItems(e, "S")).toEqual(["one", "two"]);
});
it("denies stale revision, role and absent capability", () => {
  const { e, p, d } = fixture();
  expect(inputPins(e, false)).toBeNull();
  expect(inputPins({ ...e, permissions: ["review"] }, true)).toBeNull();
  expect(() => executionPayload({ ...e, revision: 3 }, p, d)).toThrow();
});
it("does not invent observations/support/status or permit foreign items", () => {
  const { e, p, d } = fixture();
  for (const item of [
    { ...d.items[0], status: "" },
    { ...d.items[0], evidence: [] },
    { ...d.items[0], item_id: "foreign" },
    {
      ...d.items[0],
      evidence: [{ artifact_id: "A", sha256: "changed", locator: "row1" }],
    },
  ])
    expect(() => executionPayload(e, p, { ...d, items: [item] })).toThrow();
  expect(
    executionPayload(e, p, {
      ...d,
      items: [{ ...d.items[0], status: "NOT_PERFORMED", evidence: [] }],
    }),
  ).toBeTruthy();
});
it("correction requires leaf pin and preserves exact item set and prior record", () => {
  const { e, p, d } = fixture();
  const prior = { id: "X", task_id: "T", selection_id: "S", items: d.items };
  e.sample_executions = [prior];
  const before = JSON.stringify(prior);
  expect(() =>
    executionPayload(e, p, { ...d, predecessor: "X", rationale: "fix" }),
  ).toThrow();
  p.correctable_executions = [
    { execution_id: "X", predecessor_digest: "exact-server-leaf" },
  ];
  expect(
    executionPayload(e, p, { ...d, predecessor: "X", rationale: "fix" })
      .predecessor_digest,
  ).toBe("exact-server-leaf");
  expect(() =>
    executionPayload(e, p, {
      ...d,
      predecessor: "X",
      rationale: "fix",
      items: [{ ...d.items[0], item_id: "two" }],
    }),
  ).toThrow();
  expect(JSON.stringify(prior)).toBe(before);
});
