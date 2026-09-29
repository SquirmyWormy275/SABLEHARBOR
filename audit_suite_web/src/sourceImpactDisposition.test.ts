import { expect, it } from "vitest";
import type { Engagement } from "./api";
import {
  acceptedDisposition,
  dispositionCommand,
  validateDispositionInputs,
  type DispositionInputs,
  type DispositionDraft,
} from "./sourceImpactDisposition";
const pin = "a".repeat(64),
  other = "b".repeat(64);
const e = {
  id: "E",
  revision: 2,
  simulated_at: "2027-01-01T09:00:00Z",
  artifacts: [{ id: "A", sha256: pin }],
} as unknown as Engagement;
const input: DispositionInputs = {
  engagement_id: "E",
  engagement_revision: 2,
  artifact_id: "A",
  comparison: {
    sha256: pin,
    artifact_id: "A",
    collected_sha256: pin,
    latest_visible_sha256: other,
    collected_version: 1,
    latest_visible_version: 2,
    simulated_as_of: "2027-01-01T09:00:00Z",
  },
  observed: {
    discovered_at: "2027-01-01T00:00:00Z",
    rechecked_at: "2027-01-01T00:00:01Z",
  },
  targets: [
    {
      sha256: pin,
      record_sha256: pin,
      reference: { id: "WP", collection: "workpapers", version: 1 },
    },
  ],
  retests: [
    {
      sha256: other,
      record_sha256: other,
      reference: { id: "TRACE", collection: "sample_executions", version: 1 },
    },
  ],
  predecessors: [{ id: "D", sha256: other, target_sha256: pin }],
};
const draft: DispositionDraft = {
  target_sha256: pin,
  disposition: "REASSESSMENT_NEEDED",
  rationale: "Changed source may affect this passage.",
  intended_action: "Inspect the exact correction before deciding further work.",
  retest_sha256: null,
  predecessor: { id: "D", sha256: other },
};
it("pins one explicit comparison and historical target without modifying work", () => {
  const command = dispositionCommand(e, input, draft, "C");
  expect(command.kind).toBe("source.impact.disposition.record");
  expect(command.payload.target_sha256).toBe(pin);
  expect(command.expected_revision).toBe(2);
  draft.rationale = "Changed locally";
  expect(command.payload.rationale).not.toBe(draft.rationale);
  expect(command.payload).not.toHaveProperty("effective");
});
it("requires an explicit exact retest link without claiming its outcome", () => {
  expect(() =>
    dispositionCommand(
      e,
      input,
      { ...draft, disposition: "RETEST_LINKED" },
      "C",
    ),
  ).toThrow();
  const c = dispositionCommand(
    e,
    input,
    { ...draft, disposition: "RETEST_LINKED", retest_sha256: other },
    "C",
  );
  expect(c.payload.retest_sha256).toBe(other);
  expect(() =>
    dispositionCommand(e, input, { ...draft, retest_sha256: other }, "C"),
  ).toThrow();
});
it("rejects stale revision, substituted target and correction predecessor", () => {
  expect(() =>
    validateDispositionInputs({ ...input, engagement_revision: 1 }, e, "A"),
  ).toThrow();
  expect(() =>
    dispositionCommand(e, input, { ...draft, target_sha256: other }, "C"),
  ).toThrow();
  expect(() =>
    dispositionCommand(
      e,
      input,
      { ...draft, predecessor: { id: "D", sha256: pin } },
      "C",
    ),
  ).toThrow();
  expect(
    dispositionCommand(
      e,
      input,
      { ...draft, predecessor: { id: "D", sha256: other } },
      "C",
    ).payload.predecessor?.id,
  ).toBe("D");
});
it("rejects excessive inventories and requires explicit bounded rationale/action", () => {
  expect(() =>
    validateDispositionInputs(
      { ...input, targets: Array(257).fill(input.targets[0]) },
      e,
      "A",
    ),
  ).toThrow();
  for (const patch of [
    { rationale: "" },
    { intended_action: "" },
    { rationale: "x".repeat(4001) },
  ])
    expect(() =>
      dispositionCommand(e, input, { ...draft, ...patch }, "C"),
    ).toThrow();
});

it("accepts only a matching appended disposition receipt, not a revision increment alone", () => {
  const c = dispositionCommand(e, input, draft, "C");
  const row = {
    id: "D2",
    version: 1,
    revision: 3,
    actor: "L",
    recorded_at: "2027-01-01T00:00:00Z",
    context_status: "CURRENT",
    personal_content_visible: true,
    ...c.payload,
    comparison: input.comparison,
    target: input.targets[0],
    retest: null,
  };
  const result = { ...e, revision: 3, source_impact_dispositions: [row] };
  expect(acceptedDisposition(e, result, "L", c)).toBe(true);
  for (const patch of [
    { actor: "OTHER" },
    { rationale: "different" },
    { target: { ...row.target, sha256: other } },
    { context_status: "CONTEXT_CHANGED" },
  ])
    expect(
      acceptedDisposition(
        e,
        { ...result, source_impact_dispositions: [{ ...row, ...patch }] },
        "L",
        c,
      ),
    ).toBe(false);
  expect(acceptedDisposition(e, { ...e, revision: 3 }, "L", c)).toBe(false);
});
