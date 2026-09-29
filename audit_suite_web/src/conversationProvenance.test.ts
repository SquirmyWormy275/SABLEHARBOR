import { describe, it, expect } from "vitest";
import type { Row } from "./api";
import { retainedPinArtifacts } from "./conversationProvenance";
const pin = {
  system_id: "portfolio:SYS",
  record_id: "R",
  version: 2,
  sha256: "a".repeat(64),
};
const artifact = {
  id: "A",
  status: "AVAILABLE",
  sha256: pin.sha256,
  source: {
    kind: "COLLECTED_COMPANY_SOURCE",
    receipt: {
      engagement_id: "E",
      source: {
        system: "SYS",
        source_system_alias: pin.system_id,
        record: "R",
        version: 2,
        sha256: pin.sha256,
      },
    },
  },
};
const e = { id: "E", artifacts: [artifact] };
describe("saved conversation source provenance", () => {
  it("links only an exact retained original using the collection alias", () =>
    expect(retainedPinArtifacts(e, pin).map((a) => a.id)).toEqual(["A"]));
  it("never redirects historical pins to newer versions or another route", () => {
    for (const delta of [
      { version: 3 },
      { system_id: "other:SYS" },
      { sha256: "b".repeat(64) },
      { record_id: "OTHER" },
    ])
      expect(retainedPinArtifacts(e, { ...pin, ...delta })).toEqual([]);
  });
  it("rejects other-engagement receipts and unavailable bytes", () => {
    expect(retainedPinArtifacts({ ...e, id: "OTHER" }, pin)).toEqual([]);
    expect(
      retainedPinArtifacts(
        { ...e, artifacts: [{ ...artifact, status: "UNAVAILABLE" } as Row] },
        pin,
      ),
    ).toEqual([]);
  });
});
