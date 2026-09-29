import { describe, it, expect } from "vitest";
import {
  selectors,
  initialConfig,
  optionDefault,
  normalizedShares,
  serializeConfiguration,
  configErrors,
} from "./configuration";
describe("approved configuration contract", () => {
  it("omits disabled prevalence and hidden parameter defaults", () => {
    const c = initialConfig();
    c.parents["MM-01"] = true;
    c.options["MM-01.01"] = { ...optionDefault(), enabled: true };
    const wire = serializeConfiguration(c);
    expect(wire).not.toHaveProperty("incomplete_evidence");
    expect(wire.selections[0].parameters).toEqual({});
    c.parents["MM-10"] = true;
    c.options["MM-10.01"] = { ...optionDefault(), enabled: true, count: 3 };
    expect(
      serializeConfiguration(c).selections.find(
        (s) => s.selector_id === "MM-10",
      )?.parameters,
    ).toEqual({ count: 3 });
  });
  it("preserves the finite public selector catalog and MM08 no-submenu rule", () => {
    expect(selectors).toHaveLength(18);
    expect(selectors.flatMap((s) => s.options)).toHaveLength(110);
    expect(selectors.find((s) => s.id === "MM-08")!.options).toEqual([]);
  });
  it("preserves Custom for the no-submenu disagreement family", () => {
    const c = initialConfig();
    c.parents["MM-08"] = true;
    c.options["MM-08"] = {
      ...optionDefault(),
      authoring: "Custom",
      custom_text: "An owner disputes the requested evidence scope.",
    };
    expect(serializeConfiguration(c).selections[0]).toMatchObject({
      selector_id: "MM-08",
      option_id: "",
      authoring_mode: "CUSTOM",
      custom_text: "An owner disputes the requested evidence scope.",
    });
  });
  it("normalizes shares proportionally with stable ties", () => {
    const c = initialConfig();
    for (const [id, share] of [
      ["MM-02.01", 1],
      ["MM-02.02", 1],
      ["MM-02.03", 1],
    ] as const)
      c.options[id] = { ...optionDefault(), enabled: true, share };
    const n = normalizedShares(c);
    expect(
      ["MM-02.01", "MM-02.02", "MM-02.03"].map((id) => n.options[id].share),
    ).toEqual([34, 33, 33]);
    c.options["MM-02.01"].share = 6;
    c.options["MM-02.02"].share = 3;
    c.options["MM-02.03"].share = 1;
    expect(
      Object.values(normalizedShares(c).options).map((o) => o.share),
    ).toEqual([60, 30, 10]);
  });
  it("keeps prevalence separate from shares and independent intensity", () => {
    const c = initialConfig();
    c.parents = { "MM-02": true, "MM-03": true, "MM-08": true };
    c.incomplete_percent = 20;
    c.options["MM-02.01"] = { ...optionDefault(), enabled: true, share: 100 };
    for (const o of selectors.find((s) => s.id === "MM-03")!.options)
      c.options[o.id] = { ...optionDefault(), enabled: true, intensity: 100 };
    c.disagreement_frequency = 1;
    c.disagreement_severity = 100;
    const wire = serializeConfiguration(c);
    expect(configErrors(c)).toEqual([]);
    expect(wire.incomplete_evidence).toEqual({
      overall: 20,
      shares: { "MM-02.01": 100 },
    });
    expect(
      wire.selections
        .filter((s) => s.selector_id === "MM-03")
        .every(
          (s) => "intensity" in s.parameters && s.parameters.intensity === 100,
        ),
    ).toBe(true);
    expect(
      wire.selections.find((s) => s.selector_id === "MM-08"),
    ).toMatchObject({
      option_id: "",
      parameters: { frequency: 1, severity: 100 },
    });
  });
  it("preserves custom authoring text and excludes disabled selections", () => {
    const c = initialConfig();
    c.parents["MM-01"] = true;
    c.options["MM-01.01"] = {
      ...optionDefault(),
      enabled: true,
      authoring: "Custom",
      custom_text: "A specific fictional circumstance",
    };
    c.options["MM-02.01"] = { ...optionDefault(), enabled: true };
    expect(serializeConfiguration(c).selections).toEqual([
      expect.objectContaining({
        selector_id: "MM-01",
        option_id: "MM-01.01",
        authoring_mode: "CUSTOM",
        custom_text: "A specific fictional circumstance",
      }),
    ]);
  });
});
