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
