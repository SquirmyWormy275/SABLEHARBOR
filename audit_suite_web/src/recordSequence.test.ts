import { expect, it } from "vitest";
import type { Engagement } from "./api";
import { recordSequence } from "./recordSequence";
it("keeps filtered order while excluding removed or ambiguous authorized rows", () => {
  const e = {
    controls: [{ id: "C1" }, { id: "C2" }, { id: "C3" }, { id: "C3" }],
  } as unknown as Engagement;
  const n = recordSequence(e, "control", ["C2", "REMOVED", "C3", "C1"], "C2");
  expect(n?.next?.id).toBe("C1");
  expect(n?.total).toBe(2);
  expect(recordSequence(e, "control", ["C2", "C2"], "C2")).toBeNull();
  expect(recordSequence(e, "instructor_key", ["C1"], "C1")).toBeNull();
});
it("walks the exact inspected procedure sequence rather than another control or task order", () => {
  const e = {
    tasks: [{ id: "T1" }, { id: "T2" }, { id: "T3" }],
  } as unknown as Engagement;
  expect(recordSequence(e, "task", ["T3", "T1"], "T3")).toMatchObject({
    position: 1,
    total: 2,
    next: { id: "T1" },
  });
  expect(recordSequence(e, "task", ["T3", "T1"], "T2")).toBeNull();
});
