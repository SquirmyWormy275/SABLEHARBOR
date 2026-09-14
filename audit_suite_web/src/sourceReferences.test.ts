import { expect, it } from "vitest";
import type { Engagement } from "./api";
import { sourceReference } from "./sourceReferences";

const engagement = () =>
  ({
    artifacts: [{ id: "A1" }],
    workpapers: [{ id: "W1", versions: [{ version: 1 }, { version: 2 }] }],
    populations: [{ id: "P1", version: 2 }],
    selections: [],
    tasks: [],
  }) as unknown as Engagement;

it("opens a retained workpaper version within its current authorized history", () => {
  expect(
    sourceReference(engagement(), {
      collection: "workpapers",
      id: "W1",
      version: 1,
    })?.kind,
  ).toBe("workpaper");
  expect(
    sourceReference(engagement(), {
      collection: "workpapers",
      id: "W1",
      version: 3,
    }),
  ).toBeNull();
});
it("does not replace a referenced population version with a different one", () => {
  expect(
    sourceReference(engagement(), {
      collection: "populations",
      id: "P1",
      version: 1,
    }),
  ).toBeNull();
});
it("rejects hidden, missing and ambiguous references", () => {
  const e = engagement();
  expect(
    sourceReference(e, { collection: "instructor_key", id: "A1" }),
  ).toBeNull();
  expect(
    sourceReference(e, { collection: "artifacts", id: "FOREIGN" }),
  ).toBeNull();
  e.artifacts.push({ id: "A1" });
  expect(sourceReference(e, { collection: "artifacts", id: "A1" })).toBeNull();
});

it("requires the exact artifact hash when the source DTO supplies a pin", () => {
  const e = engagement();
  e.artifacts[0].sha256 = "a".repeat(64);
  expect(
    sourceReference(e, {
      collection: "artifacts",
      id: "A1",
      sha256: "a".repeat(64),
    })?.kind,
  ).toBe("artifact");
  expect(
    sourceReference(e, {
      collection: "artifacts",
      id: "A1",
      sha256: "b".repeat(64),
    }),
  ).toBeNull();
  expect(
    sourceReference(e, { collection: "artifacts", id: "A1", sha256: null }),
  ).toBeNull();
});
