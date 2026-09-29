import { expect, it } from "vitest";
import {
  sameDebriefValue,
  debriefPin,
  safeDebriefFilename,
} from "./instructorDebrief";
it("compares exact selected structure independent of JSON object key order", () => {
  const selected = {
    sections: [{ issue_ids: ["I1", "I2"], explanation: "Authored" }],
    revision: 1,
  };
  expect(
    sameDebriefValue(selected, {
      revision: 1,
      sections: [{ explanation: "Authored", issue_ids: ["I1", "I2"] }],
    }),
  ).toBe(true);
  expect(sameDebriefValue(selected, { ...selected, revision: true })).toBe(
    false,
  );
  expect(
    sameDebriefValue(selected, {
      ...selected,
      sections: [{ issue_ids: ["I2", "I1"], explanation: "Authored" }],
    }),
  ).toBe(false);
  expect(sameDebriefValue(selected, { ...selected, hidden: "extra" })).toBe(
    false,
  );
});
it("requires exact SHA pins and safe portable leaf names", () => {
  expect(debriefPin("a".repeat(64))).toBe(true);
  expect(debriefPin("A".repeat(64))).toBe(false);
  expect(safeDebriefFilename("debrief-release-1.html")).toBe(true);
  for (const name of [
    "../key.json",
    "/private/key",
    "a\\b",
    "data:text/html",
    "../",
    "",
    "a\n.html",
  ])
    expect(safeDebriefFilename(name)).toBe(false);
});

import {
  validateDebriefDraft,
  type DebriefOptions,
  type DebriefDraft,
} from "./instructorDebrief";
const options: DebriefOptions = {
  engagement_id: "E",
  revision: 3,
  key_manifest_sha256: "f".repeat(64),
  recipients: [{ id: "L", name: "Learner" }],
  issues: [
    { id: "I", title: "Selected issue" },
    { id: "J", title: "Other issue" },
  ],
  expectations: [{ id: "X", title: "Procedure", issue_ids: ["I"] }],
  artifacts: [
    { id: "A", title: "original.txt", sha256: "a".repeat(64), bytes: 20 },
  ],
};
function draft(): DebriefDraft {
  return {
    recipient_id: "L",
    expected_revision: 3,
    learner_revision: 1,
    title: "Selected explanation",
    predecessor_release_id: null,
    sections: [
      {
        issue_ids: ["I"],
        expectation_ids: ["X"],
        explanation: "Instructor interpretation",
        limitations: "Not independently validated",
        prompts: ["Which evidence supports this?"],
        annotations: [
          {
            artifact_id: "A",
            sha256: "a".repeat(64),
            note: "Selected support",
            locator: null,
            attach: false,
          },
        ],
      },
    ],
  };
}
it("requires exact authorized selection and preserves historical learner revision and attachment opt-in", () => {
  const d = draft();
  const valid = validateDebriefDraft(d, options);
  expect(valid.learner_revision).toBe(1);
  expect(valid.sections[0].annotations[0].attach).toBe(false);
  valid.sections[0].explanation = "changed";
  expect(d.sections[0].explanation).toBe("Instructor interpretation");
});
it("rejects foreign selections, unrelated expectations, substituted originals and oversize sections", () => {
  for (const change of [
    (d: DebriefDraft) => (d.recipient_id = "other"),
    (d: DebriefDraft) => (d.expected_revision = 2),
    (d: DebriefDraft) => (d.learner_revision = 4),
    (d: DebriefDraft) => (d.sections[0].issue_ids = ["J"]),
    (d: DebriefDraft) => (d.sections[0].annotations[0].sha256 = "b".repeat(64)),
    (d: DebriefDraft) =>
      (d.sections = Array.from({ length: 11 }, () => d.sections[0])),
  ]) {
    const d = draft();
    change(d);
    expect(() => validateDebriefDraft(d, options)).toThrow();
  }
});

import {
  debriefPreviewMatches,
  exportPreviewMatches,
  type DebriefPreview,
  type DebriefExportPreview,
} from "./instructorDebrief";
function preview(): DebriefPreview {
  const d = draft();
  return {
    delivered: false,
    preview_sha256: "c".repeat(64),
    preview: {
      id: "P",
      engagement_id: "E",
      instructor_id: "T",
      recipient_id: "L",
      revision: 3,
      key_manifest_sha256: options.key_manifest_sha256,
      expires_at: new Date(Date.now() + 60000).toISOString(),
      content: {
        stage: "EXPLANATION",
        text: d.title,
        pointers: [],
        document: {
          schema: "SELECTED_INSTRUCTOR_DEBRIEF_V1",
          source_references: [
            {
              artifact_id: "A",
              artifact_sha256: "a".repeat(64),
              status: "UNRECORDED",
              native: null,
            },
          ],
          title: d.title,
          version: 1,
          predecessor: null,
          key_manifest_sha256: options.key_manifest_sha256,
          learner: {
            actor_id: "L",
            revision: 1,
            state_sha256: "d".repeat(64),
            event_sha256: "d".repeat(64),
            history_sha256: "d".repeat(64),
            qualification: "SHARED",
          },
          qualification: "UNVALIDATED",
          sections: d.sections.map((s) => ({
            ...s,
            issues: s.issue_ids.map((id) => ({
              id,
              control_ids: ["C"],
              claim: "Selected authored claim",
            })),
            expectations: s.expectation_ids.map((id) => ({
              id,
              issue_ids: ["I"],
              procedure: "Selected procedure",
              acceptable_alternatives: [],
            })),
          })),
        },
      },
    },
  };
}
it("binds preview to exact selected sections, actor, recipient, Key and historical revision", () => {
  expect(debriefPreviewMatches(preview(), draft(), options, "E", "T")).toBe(
    true,
  );
  for (const mutate of [
    (p: DebriefPreview) =>
      p.preview.content.document.sections[0].issues.push({
        id: "UNSELECTED",
        control_ids: [],
        claim: "secret",
      }),
    (p: DebriefPreview) => (p.preview.content.document.learner.revision = 3),
    (p: DebriefPreview) => (p.preview.recipient_id = "other"),
    (p: DebriefPreview) => (p.preview.key_manifest_sha256 = "e".repeat(64)),
    (p: DebriefPreview) =>
      (p.preview.content.document.sections[0].annotations[0].attach = true),
  ]) {
    const p = preview();
    mutate(p);
    expect(debriefPreviewMatches(p, draft(), options, "E", "T")).toBe(false);
  }
});
it("binds export preview to actor/release pins and rejects unsafe members or oversized ZIP", () => {
  const p: DebriefExportPreview = {
    exported: false,
    preview_sha256: "b".repeat(64),
    preview: {
      id: "XP",
      actor_id: "L",
      engagement_id: "E",
      release_id: "R",
      release_sha256: "a".repeat(64),
      filename: "selected-debrief.zip",
      sha256: "c".repeat(64),
      bytes: 500,
      members: [
        { name: "originals/01.bin", bytes: 30, sha256: "d".repeat(64) },
      ],
      expires_at: new Date(Date.now() + 60000).toISOString(),
    },
  };
  const valid = (v: DebriefExportPreview) =>
    exportPreviewMatches(v, "E", "L", "R", "a".repeat(64));
  expect(valid(p)).toBe(true);
  for (const mutate of [
    (v: DebriefExportPreview) => (v.preview.actor_id = "other"),
    (v: DebriefExportPreview) => (v.preview.bytes = 21 * 1024 * 1024),
    (v: DebriefExportPreview) => (v.preview.members[0].name = "../hidden.json"),
    (v: DebriefExportPreview) => (v.preview.expires_at = "2000-01-01"),
  ]) {
    const v = structuredClone(p);
    mutate(v);
    expect(valid(v)).toBe(false);
  }
});
