import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import type { Engagement } from "./api";
import { EvidenceContext } from "./EvidenceContext";
import {
  evidenceContextKey,
  recordedEvidenceContext,
  resolveEvidenceContextReference,
} from "./evidenceContext";

function fixture(): Engagement {
  return {
    id: "E",
    revision: 1,
    permissions: ["learn"],
    scope: { boundaries: ["corporate"] },
    artifacts: [
      {
        id: "A",
        status: "AVAILABLE",
        sha256: "a".repeat(64),
        request_id: "R",
        name: "C9 passed payroll.xlsx",
        source: {
          receipt: {
            source: {
              system: "native",
              record: "r",
              version: 2,
              provenance: { control_ids: ["C1", "foreign-control"] },
            },
          },
        },
      },
    ],
    requests: [
      {
        id: "R",
        purpose: "Inspect the submitted reconciliation.",
        control_id: "C2",
      },
    ],
    controls: [{ id: "C1" }, { id: "C2" }],
    tasks: [
      { id: "T1", control_id: "C1", boundary_id: "corporate" },
      { id: "T2", control_id: "C2", boundary_id: "other" },
      {
        id: "old",
        control_id: "C1",
        applicability: "PRIOR_SCOPE_REQUIRES_REASSESSMENT",
      },
    ],
    workpapers: [
      {
        id: "W",
        control_id: "C1",
        versions: [
          { version: 1, evidence_ids: ["A"], task_ids: ["T1"] },
          { version: 2, evidence_ids: ["OTHER"], task_ids: ["T1"] },
          { version: 3, evidence_ids: ["A"], task_ids: [] },
        ],
      },
      {
        id: "unlinked",
        control_id: "C1",
        versions: [{ version: 1, task_ids: ["T1"] }],
      },
    ],
  } as unknown as Engagement;
}
describe("recorded artifact context", () => {
  it("separates source declarations, request context and exact-version citations", () => {
    const e = fixture(),
      c = recordedEvidenceContext(e, "A")!;
    expect(c.declaredControls.map((r) => r.id)).toEqual(["C1"]);
    expect(c.requestedControl?.id).toBe("C2");
    expect(c.procedures.map((r) => r.id)).toEqual(["T1"]);
    expect(c.citations.map((r) => [r.paper.id, r.version, r.taskIds])).toEqual([
      ["W", 1, ["T1"]],
      ["W", 3, []],
    ]);
    expect(c.declarationUnavailable).toBe(true);
    expect(JSON.stringify(c)).not.toContain('"id":"C9"');
  });
  it("requires available unique artifacts and unique historical versions", () => {
    const e = fixture();
    e.artifacts[0].status = "QUARANTINED";
    expect(recordedEvidenceContext(e, "A")).toBeNull();
    e.artifacts[0].status = "AVAILABLE";
    e.artifacts.push({ ...e.artifacts[0] });
    expect(recordedEvidenceContext(e, "A")).toBeNull();
    const other = fixture();
    (other.workpapers[0].versions as unknown[]).push({
      version: 1,
      evidence_ids: ["A"],
    });
    expect(
      recordedEvidenceContext(other, "A")?.citations.map((c) => c.version),
    ).toEqual([3]);
  });
  it("refreshes keys on identity, source, scope, authority and connection changes", () => {
    const e = fixture(),
      key = evidenceContextKey(e, "U", "A");
    for (const patch of [
      { id: "foreign" },
      { revision: 2 },
      { permissions: [] },
      { scope: { boundaries: ["other"] } },
      { company_source_binding: { branch: "other" } },
      { evidence_acquisition: "changed" },
      { artifacts: [{ ...e.artifacts[0], sha256: "b".repeat(64) }] },
    ])
      expect(
        evidenceContextKey({ ...e, ...patch } as Engagement, "U", "A"),
      ).not.toBe(key);
    expect(evidenceContextKey(e, "OTHER", "A")).not.toBe(key);
    expect(
      recordedEvidenceContext({ ...e, permissions: ["review"] }, "A")?.canDraft,
    ).toBe(false);
  });
  it("rejects unavailable and unpinned workpaper navigation targets", () => {
    const e = fixture();
    expect(
      resolveEvidenceContextReference(e, {
        collection: "workpapers",
        id: "W",
        version: 1,
      })?.id,
    ).toBe("W");
    expect(
      resolveEvidenceContextReference(e, {
        collection: "workpapers",
        id: "W",
        version: 99,
      }),
    ).toBeUndefined();
    expect(
      resolveEvidenceContextReference(e, { collection: "workpapers", id: "W" }),
    ).toBeUndefined();
    expect(
      resolveEvidenceContextReference(e, {
        collection: "controls",
        id: "foreign",
      }),
    ).toBeUndefined();
  });
  it("renders factual labels safely without changing formal records or draft text", () => {
    const e = fixture();
    e.requests[0].purpose = "<script>bad</script>";
    const before = JSON.stringify(e),
      draft = { text: "Unsubmitted work" };
    const html = renderToStaticMarkup(
      createElement(EvidenceContext, {
        engagement: e,
        artifactId: "A",
        viewerId: "U",
        onOpen: () => {},
        onStartDraft: () => {},
      }),
    );
    expect(html).toContain("&lt;script&gt;bad&lt;/script&gt;");
    expect(html).toContain(
      "Related by control only; evidence support is not established.",
    );
    expect(html).toContain(
      "Citation records use, not acceptance or successful testing.",
    );
    expect(html).toContain('aria-expanded="true"');
    expect(html).toContain("Open workpaper draft");
    expect(JSON.stringify(e)).toBe(before);
    expect(draft.text).toBe("Unsubmitted work");
    const restricted = renderToStaticMarkup(
      createElement(EvidenceContext, {
        engagement: { ...e, permissions: ["review"] },
        artifactId: "A",
        viewerId: "U",
        onOpen: () => {},
        onStartDraft: () => {},
      }),
    );
    expect(restricted).not.toContain(
      "Open workpaper draft",
    );
  });
});
