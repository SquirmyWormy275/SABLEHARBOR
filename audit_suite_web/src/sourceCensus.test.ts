import { describe, it, expect } from "vitest";
import { censusQuery } from "./sourceCensus";
describe("source-record census query", () => {
  it("preserves explicit offsets and independent version/undated policies", () =>
    expect(
      censusQuery(
        "LATEST_VISIBLE_PER_RECORD",
        "2027-03-14T00:00:00-07:00",
        "2027-03-15T00:00:00-06:00",
        "INCLUDE_UNDATED_STRATUM",
      ),
    ).toEqual({
      version_policy: "LATEST_VISIBLE_PER_RECORD",
      event_window: {
        start: "2027-03-14T00:00:00-07:00",
        end: "2027-03-15T00:00:00-06:00",
      },
      unknown_event_policy: "INCLUDE_UNDATED_STRATUM",
    }));
  it("rejects date-only/naive/impossible dates instead of guessing source time", () => {
    for (const start of [
      "2027-01-01",
      "2027-01-01T00:00:00",
      "2027-02-30T00:00:00Z",
      "2027-01-01T24:00:00Z",
      "2027-01-01T00:00:00+25:00",
    ])
      expect(() =>
        censusQuery(
          "ALL_VISIBLE_VERSIONS",
          start,
          "2028-01-01T00:00:00Z",
          "EXCLUDE",
        ),
      ).toThrow();
  });
  it("validates ordering by instant, including offsets", () =>
    expect(() =>
      censusQuery(
        "ALL_VISIBLE_VERSIONS",
        "2027-01-01T00:00:00-08:00",
        "2027-01-01T01:00:00Z",
        "EXCLUDE",
      ),
    ).toThrow(/after/));
  it("does not silently choose unknown policies or accept zero-length windows", () => {
    expect(() =>
      censusQuery(
        "ALL",
        "2027-01-01T00:00:00Z",
        "2028-01-01T00:00:00Z",
        "EXCLUDE",
      ),
    ).toThrow();
    expect(() =>
      censusQuery(
        "ALL_VISIBLE_VERSIONS",
        "2027-01-01T00:00:00Z",
        "2027-01-01T00:00:00Z",
        "EXCLUDE",
      ),
    ).toThrow();
  });
});
