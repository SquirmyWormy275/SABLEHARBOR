import { expect, it } from "vitest";
import {
  assertKeyContext,
  assertKeyDetail,
  filterKeys,
  keyOption,
  type InstructorIndex,
  type InstructorDetail,
  type KeyEntry,
} from "./instructorKey";
const entry = (id: string, professional = "UNVALIDATED"): KeyEntry => ({
  id,
  raw_sha256: "a".repeat(64),
  canonical_sha256: "b".repeat(64),
  key_sha256: "c".repeat(64),
  review: {
    professional,
    causal_validation: "NOT_RUN",
    grading: "NOT_RUN",
    gaps: ["SOURCE_LINK_NOT_TYPED"],
  },
});
const context = () => ({
  status: "UNBOUND_REFERENCE_LIBRARY" as const,
  binding: { status: "NOT_BOUND" as const, engagement_id: "ENG-1" },
  archive: { sha256: "d".repeat(64) },
});
const detail = (): InstructorDetail => ({
  ...context(),
  key: {
    schema: "PRIVATE_INSTRUCTOR_KEY_V1",
    audience: "INSTRUCTOR_ONLY",
    id: "MM-01.01.V01",
    source: {
      raw_sha256: "a".repeat(64),
      canonical_sha256: "b".repeat(64),
      schema_version: "1.0",
    },
    review: entry("x").review,
    explanation: {
      title: "Neutral",
      mechanism: {},
      facts: [],
      actor_knowledge: [],
      artifacts: [],
      events: [],
      playable_paths: [],
      rubric: {
        supported_conclusions: ["Bounded"],
        acceptable_alternatives: ["Further work"],
        unsupported_guesses: ["Automatic pass"],
      },
    },
    graph: {},
  },
});
it("filters exact selector/option/review and searches only actual indexed fields", () => {
  const rows = [
    entry("MM-01.01.V01"),
    entry("MM-01.02.V01", "DISPUTED"),
    entry("MM-08.INTERNAL.V01"),
  ];
  expect(
    filterKeys(rows, {
      query: "source_link",
      selector: "MM-01",
      option: "MM-01.01",
      review: "UNVALIDATED",
    }).map((e) => e.id),
  ).toEqual(["MM-01.01.V01"]);
  expect(
    filterKeys(rows, {
      query: "hidden outcome not in index",
      selector: "all",
      option: "all",
      review: "all",
    }),
  ).toEqual([]);
  expect(keyOption("MM-08.INTERNAL.V01")).toBe("MM-08.INTERNAL");
});
it("requires actual unbound archive context and engagement identity", () => {
  expect(() => assertKeyContext(context(), "ENG-1")).not.toThrow();
  expect(() => assertKeyContext(context(), "ENG-2")).toThrow();
  expect(() =>
    assertKeyContext(
      { ...context(), status: "ACTIVE" } as unknown as InstructorIndex,
      "ENG-1",
    ),
  ).toThrow();
  expect(() =>
    assertKeyContext({ ...context(), archive: { sha256: "invalid" } }, "ENG-1"),
  ).toThrow();
});
it("accepts only detail pinned to selected original and canonical source", () => {
  const e = entry("MM-01.01.V01");
  expect(() =>
    assertKeyDetail(detail(), e, "ENG-1", "d".repeat(64)),
  ).not.toThrow();
  const changed = detail();
  changed.key.source.raw_sha256 = "e".repeat(64);
  expect(() => assertKeyDetail(changed, e, "ENG-1", "d".repeat(64))).toThrow();
  changed.key.source.raw_sha256 = e.raw_sha256;
  changed.key.source.canonical_sha256 = "e".repeat(64);
  expect(() => assertKeyDetail(changed, e, "ENG-1", "d".repeat(64))).toThrow();
});
it("rejects archive switches, wrong keys and wrong audience", () => {
  const e = entry("MM-01.01.V01");
  expect(() => assertKeyDetail(detail(), e, "ENG-1", "e".repeat(64))).toThrow();
  const changed = detail();
  changed.key.id = "MM-01.01.V02";
  expect(() => assertKeyDetail(changed, e, "ENG-1", "d".repeat(64))).toThrow();
  changed.key.id = e.id;
  (changed.key as { audience: string }).audience = "LEARNER";
  expect(() => assertKeyDetail(changed, e, "ENG-1", "d".repeat(64))).toThrow();
});
