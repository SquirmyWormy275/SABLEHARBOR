import { describe, expect, it } from "vitest";
import type { Engagement } from "./api";
import { createTableMemory } from "./tableMemory";
import {
  currentViewResponse,
  exactReferenceDescriptor,
  resolveSavedViewReference,
  restoredNavigation,
  savedViewContext,
  type SavedView,
} from "./savedViews";
const e = {
  id: "E",
  revision: 5,
  permissions: ["learn"],
  scope: { programs: ["SOC2"] },
  workpapers: [
    { id: "W", version: 2, versions: [{ version: 1 }, { version: 2 }] },
  ],
} as unknown as Engagement;
const ref = {
  kind: "workpaper" as const,
  id: "W",
  version: 1,
  sha256: "a".repeat(64),
};
const view = {
  id: "V",
  engagement_id: "E",
  version: 3,
  current_engagement_revision: 5,
  status: "ACTIVE",
  context_status: "CURRENT",
  personal_content_visible: true,
  restorable: true,
  navigation: {
    section: "review",
    query: "report",
    framework: "all",
    scroll_top: 12,
    reference: ref,
    table: { id: "workpapers", query: "Report", page: 2, sort: "title" },
  },
} as SavedView;
describe("explicit saved view restore", () => {
  it("rejects mismatched engagement, revision and exact saved-view versions", () => {
    for (const changed of [
      { engagement_id: "OTHER" },
      { current_engagement_revision: 4 },
      { id: "OTHER" },
      { version: 4 },
    ])
      expect(() =>
        restoredNavigation({ ...view, ...changed }, e, "V", 3),
      ).toThrow();
    expect(currentViewResponse(view, e, "V")).toBe(true);
  });
  it("never restores redacted or suspended personal content", () => {
    for (const changed of [
      { personal_content_visible: false },
      { context_status: "CONTEXT_CHANGED" },
      { restorable: false },
      { status: "CLEARED" },
    ])
      expect(() =>
        restoredNavigation({ ...view, ...changed }, e, "V", 3),
      ).toThrow();
  });
  it("preserves historical workpaper version and rejects ambiguous or missing versions", () => {
    expect(
      restoredNavigation(view, e, "V", 3).navigation.reference?.version,
    ).toBe(1);
    expect(resolveSavedViewReference(e, { ...ref, version: 9 })).toBeNull();
    expect(
      resolveSavedViewReference(
        { ...e, workpapers: [...e.workpapers, ...e.workpapers] },
        ref,
      ),
    ).toBeNull();
    expect(
      resolveSavedViewReference(
        {
          ...e,
          workpapers: [{ id: "W", versions: [{ version: 1 }, { version: 1 }] }],
        },
        ref,
      ),
    ).toBeNull();
  });
  it("requires server link to match explicit version and a digest", () => {
    expect(exactReferenceDescriptor(ref, { ...ref, version: 2 })).toBe(false);
    expect(exactReferenceDescriptor({ ...ref, sha256: "" }, ref)).toBe(false);
    expect(exactReferenceDescriptor(ref, ref)).toBe(true);
  });
  it("rejects unrelated table restoration and isolates authority/revision contexts", () => {
    expect(() =>
      restoredNavigation(
        {
          ...view,
          navigation: {
            ...view.navigation!,
            table: { id: "artifacts", query: "", sort: "", page: 0 },
          },
        },
        e,
        "V",
        3,
      ),
    ).toThrow();
    expect(savedViewContext(e, "A")).not.toBe(savedViewContext(e, "B"));
    expect(savedViewContext(e, "A")).not.toBe(
      savedViewContext({ ...e, revision: 6 }, "A"),
    );
  });
});
describe("table restoration subscription", () => {
  it("restores mounted tables without ordinary-write feedback loops", () => {
    const memory = createTableMemory(),
      observed: unknown[] = [];
    const stop = memory.subscribe("workpapers", (value) => {
      observed.push(value);
      memory.write("workpapers", value);
    });
    memory.restore("workpapers", { query: "saved", sort: "title", page: 4 });
    expect(observed).toHaveLength(1);
    expect(memory.read("workpapers")).toEqual({
      query: "saved",
      sort: "title",
      page: 4,
    });
    stop();
    memory.restore("workpapers", { query: "new", sort: "", page: 0 });
    expect(observed).toHaveLength(1);
  });
  it("retains restoration hints after navigation without crossing providers", () => {
    const first = createTableMemory(),
      second = createTableMemory();
    first.restore("controls", { query: "saved", sort: "id", page: 8 });
    expect(first.restoration("controls")?.page).toBe(8);
    expect(second.read("controls").query).toBe("");
    first.dismissRestoration("controls");
    expect(first.restoration("controls")).toBeNull();
  });
});
