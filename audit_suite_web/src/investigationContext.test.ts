import { describe, it, expect } from "vitest";
import type { Engagement } from "./api";
import {
  resolveContextLink,
  selectedVersion,
  contextsPath,
  contextAllowsOpen,
} from "./investigationContext";
const link = {
  kind: "control" as const,
  id: "C1",
  version: null,
  sha256: "a".repeat(64),
};
const e = {
  id: "E1",
  controls: [{ id: "C1", title: "Neutral" }],
} as unknown as Engagement;
describe("personal investigation links", () => {
  it("never opens missing or changed pins", () => {
    for (const status of ["MISSING", "CONTENT_CHANGED", "OUT_OF_SCOPE"])
      expect(resolveContextLink(e, link, status)).toBeNull();
  });
  it("resolves only unique current authorized rows", () => {
    expect(resolveContextLink(e, link, "EXACT_PIN_AVAILABLE")?.id).toBe("C1");
    expect(
      resolveContextLink(
        { ...e, controls: [...e.controls, ...e.controls] },
        link,
        "EXACT_PIN_AVAILABLE",
      ),
    ).toBeNull();
  });
  it("preserves explicit workpaper version selection", () => {
    expect(
      selectedVersion("workpaper", {
        id: "W1",
        versions: [{ version: 1 }, { version: 2 }],
      }),
    ).toBe(2);
    expect(selectedVersion("workpaper", { id: "W1" })).toBeNull();
  });
  it("escapes context endpoint identity", () =>
    expect(contextsPath("x/y")).toContain("x%2Fy"));
});

it("blocks unchanged-scope links when source or permission basis changed or was never recorded", () => {
  for (const context_status of [
    "CONTEXT_CHANGED",
    "BASIS_UNRECORDED",
    undefined,
  ] as const)
    expect(contextAllowsOpen({ scope_status: "CURRENT", context_status })).toBe(
      false,
    );
  expect(
    contextAllowsOpen({ scope_status: "CURRENT", context_status: "CURRENT" }),
  ).toBe(true);
  expect(
    contextAllowsOpen({
      scope_status: "SCOPE_CHANGED",
      context_status: "CURRENT",
    }),
  ).toBe(false);
});
