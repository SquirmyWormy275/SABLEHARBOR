import { expect, it } from "vitest";
import { populationQuery, sourceMonth } from "./CompanyPopulation";
it("keeps explicit source units and source calendar", () => {
  expect(sourceMonth("2027-01-01")).toBe(1);
  expect(sourceMonth("2031-12-31")).toBe(60);
  expect(
    populationQuery("contract_versions", "base", "1", "12", "u1,u2").units,
  ).toEqual(["u1", "u2"]);
});
it("rejects missing or repeated units", () => {
  for (const units of ["", "u1,u1"])
    expect(() =>
      populationQuery("contract_versions", "base", "1", "12", units),
    ).toThrow();
});
it("rejects unsupported tables and invalid ranges", () => {
  for (const [table, a, b] of [
    ["other", "1", "12"],
    ["contract_versions", "1.5", "12"],
    ["contract_versions", "12", "1"],
  ])
    expect(() => populationQuery(table, "base", a, b, "u1")).toThrow();
});
