import { expect, it, vi } from "vitest";
import type { Engagement } from "./api";
import {
  acceptsPreview,
  loadTextPreview,
  previewKey,
  supportingTasks,
  textPreviewAllowed,
} from "./workpaperSupport";
const artifact = {
  id: "A1",
  status: "AVAILABLE",
  sha256: "a".repeat(64),
  mime: "text/plain",
  bytes: 4,
};
const fixture = () =>
  ({
    id: "E1",
    revision: 1,
    permissions: ["learn"],
    artifacts: [artifact],
    controls: [{ id: "C1" }],
    tasks: [
      { id: "T1", control_id: "C1" },
      { id: "T2", control_id: "C2" },
    ],
  }) as unknown as Engagement;
it("rejects stale responses across principal, engagement, revision, hash and availability", () => {
  const e = fixture(),
    key = previewKey("U1", e, artifact);
  expect(acceptsPreview(key, "U1", e, "A1")).toBe(true);
  for (const changed of [
    { ...e, id: "E2" },
    { ...e, revision: 2 },
    { ...e, artifacts: [{ ...artifact, sha256: "b".repeat(64) }] },
    { ...e, artifacts: [{ ...artifact, status: "QUARANTINED" }] },
  ])
    expect(acceptsPreview(key, "U1", changed, "A1")).toBe(false);
  expect(acceptsPreview(key, "U2", e, "A1")).toBe(false);
});
it("uses actual relationships without altering draft values or allowing native HTML", () => {
  const values = Object.freeze({ text: "Unsaved draft", control_id: "C1" });
  expect(
    supportingTasks(fixture(), values.control_id).map((r) => r.id),
  ).toEqual(["T1"]);
  expect(supportingTasks(fixture(), "C2")).toEqual([]);
  expect(values.text).toBe("Unsaved draft");
  expect(textPreviewAllowed({ ...artifact, mime: "text/html" })).toBe(false);
});
it("fails denied downloads and mismatched hash", async () => {
  const mock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response("denied", { status: 403 }))
    .mockResolvedValueOnce(new Response("data"));
  try {
    await expect(
      loadTextPreview("E1", artifact, new AbortController().signal),
    ).rejects.toThrow("403");
    await expect(
      loadTextPreview("E1", artifact, new AbortController().signal),
    ).rejects.toThrow("hash");
  } finally {
    mock.mockRestore();
  }
});
it("deduplicates explicit appended references without touching other draft fields", async () => {
  const { appendEvidenceReference } = await import("./workpaperSupport");
  expect(appendEvidenceReference("A1, A2\nA1", "A2")).toEqual(["A1", "A2"]);
  expect(appendEvidenceReference(["A1"], "A3")).toEqual(["A1", "A3"]);
});

it("procedure picker excludes task boundaries outside current scope", () => {
  const e = fixture();
  e.scope = { boundaries: ["corporate"] } as Engagement["scope"];
  e.tasks.push({ id: "T3", control_id: "C1", boundary_id: "other" });
  expect(supportingTasks(e, "C1").map((t) => t.id)).toEqual(["T1"]);
});
