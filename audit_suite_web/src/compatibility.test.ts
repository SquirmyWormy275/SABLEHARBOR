import { describe, expect, it } from "vitest";
import { compatibleWorkpaperValues, supports } from "./compatibility";

describe("older service capabilities", () => {
  it("requires explicit optional support while preserving existing AI", () => {
    const legacy = {
      voice: true,
      custom_authoring: true,
      experimental_review: true,
    };
    expect(supports(legacy, "personal_drafts")).toBe(false);
    expect(supports(legacy, "workpaper_procedure_links")).toBe(false);
    expect(supports(legacy, "instructor_reference_library")).toBe(false);
    expect(supports(legacy, "voice")).toBe(true);
    expect(supports({ personal_drafts: true }, "personal_drafts")).toBe(true);
  });
  it("omits unsupported task fields without losing draft text or mutating values", () => {
    const input = {
      text: "Existing draft",
      evidence_ids: "A1",
      task_ids: ["T1"],
    };
    expect(compatibleWorkpaperValues("workpaper.update", input, {})).toEqual({
      text: "Existing draft",
      evidence_ids: "A1",
    });
    expect(input.task_ids).toEqual(["T1"]);
    expect(
      compatibleWorkpaperValues("workpaper.add", input, {
        workpaper_procedure_links: true,
      }),
    ).toBe(input);
  });
});
