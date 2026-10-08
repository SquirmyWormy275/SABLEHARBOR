import { expect, it } from "vitest";
import {
  filterKeys,
  semanticSearchTerms,
  type KeyEntry,
} from "./instructorKey";

const fields = [
  "title",
  "mechanism",
  "facts",
  "actor_knowledge",
  "artifacts",
  "events",
  "playable_paths",
];
const counts = Object.fromEntries(
  fields.map((f) => [f, f === "title" || f === "facts" ? 1 : 0]),
);
const entry: KeyEntry = {
  id: "MM-13.03.V01",
  raw_sha256: "a".repeat(64),
  canonical_sha256: "b".repeat(64),
  key_sha256: "c".repeat(64),
  review: {
    professional: "UNVALIDATED",
    causal_validation: "NOT_RUN",
    grading: "NOT_RUN",
    gaps: [],
  },
  semantic_search: {
    schema: "PRIVATE_AUTHORED_SEMANTIC_SEARCH_V1",
    basis:
      "LITERAL_AUTHORED_SCALARS_NOT_VERIFIED_PERSON_ASSET_PERIOD_OR_CAUSALITY",
    id: "MM-13.03.V01",
    source_sha256: "a".repeat(64),
    canonical_sha256: "b".repeat(64),
    key_sha256: "c".repeat(64),
    coverage_fields: fields,
    included_by_field: counts,
    omitted_by_field: Object.fromEntries(fields.map((f) => [f, 0])),
    terms: [
      { pointer: "/title", text: "Literal authored exception" },
      { pointer: "/facts/0/statement", text: "P014 inspected ASSET-LAB" },
    ],
    total_scalars: 2,
    omitted_scalars: 0,
    truncated_values: 0,
  },
};
const filter = {
  query: "ASSET-LAB",
  selector: "all",
  option: "all",
  review: "all",
};

it("uses source-bound authored terms while preserving optional thin metadata compatibility", () => {
  expect(filterKeys([entry], filter)).toEqual([entry]);
  const old = { ...entry };
  delete old.semantic_search;
  expect(semanticSearchTerms(old)).toEqual([]);
  expect(filterKeys([old], { ...filter, query: old.id })).toEqual([old]);
  expect(filterKeys([old], filter)).toEqual([]);
});
it("refuses semantic terms credited to another source or undeclared private field", () => {
  for (const metadata of [
    { ...entry.semantic_search!, key_sha256: "d".repeat(64) },
    {
      ...entry.semantic_search!,
      terms: [
        { pointer: "/private_credentials", text: "not admitted" },
        { pointer: "/title", text: "title" },
      ],
    },
  ])
    expect(() =>
      semanticSearchTerms({ ...entry, semantic_search: metadata }),
    ).toThrow();
});
