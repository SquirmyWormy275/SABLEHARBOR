import { describe, it, expect } from "vitest";
import {
  ownedSystems,
  sourcePin,
  addSourcePin,
  samePins,
} from "./meetingSources";
const pin = {
  system_id: "store:original",
  record_id: "r1",
  version: 2,
  sha256: "a".repeat(64),
};
describe("explicit meeting sources", () => {
  it("restricts systems to actual selected participant ownership", () =>
    expect(
      ownedSystems(
        [
          { id: "1", system: "a", owner: "P1" },
          { id: "2", system: "b", owner: "P2" },
        ],
        "P1",
      ).map((s) => s.system),
    ).toEqual(["a"]));
  it("preserves alias and original exact digest/version with registry verification", () => {
    const row = {
      id: "1",
      record: "r1",
      version: 2,
      sha256: pin.sha256,
      source_system_alias: pin.system_id,
      registry_sha256: "r",
    };
    expect(sourcePin(row, pin.system_id, "r")).toEqual(pin);
    expect(sourcePin(row, "other", "r")).toBeNull();
    expect(sourcePin(row, pin.system_id, "changed")).toBeNull();
    expect(sourcePin({ ...row, version: "2" }, pin.system_id, "r")).toBeNull();
  });
  it("rejects duplicate records or a fifth record without mutating selection", () => {
    const old = [pin];
    expect(() => addSourcePin(old, { ...pin, version: 3 })).toThrow();
    expect(old).toEqual([pin]);
    expect(() =>
      addSourcePin(
        Array.from({ length: 4 }, (_, i) => ({ ...pin, record_id: String(i) })),
        pin,
      ),
    ).toThrow();
  });
  it("makes new selection copies and compares exact pins for delayed acceptance", () => {
    const copy = addSourcePin([], pin);
    copy[0].version = 3;
    expect(pin.version).toBe(2);
    expect(samePins(copy, [pin])).toBe(false);
    expect(samePins([pin], [{ ...pin }])).toBe(true);
  });
});
