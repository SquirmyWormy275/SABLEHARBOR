import { describe, expect, it } from "vitest";
import type { Engagement } from "./api";
import {
  checkpointRecord,
  verifyCheckpoint,
  type VisitCheckpoint,
} from "./visitCheckpoint";
const e = { id: "E", revision: 4 } as Engagement;
const pin = (kind = "artifact", version: number | null = 2, id = "A") => ({
  reference: { kind, id, version, sha256: "a".repeat(64) },
  record_sha256: "b".repeat(64),
});
const base = () =>
  ({
    engagement_id: "E",
    current_engagement_revision: 4,
    version: 1,
    status: "CURRENT",
    formal_work_mutated: false,
    supported_kinds: ["artifact"],
  }) as VisitCheckpoint;
const comparison = () =>
  ({
    ...base(),
    changes: [{ change: "CHANGED", prior: pin("artifact", 1), current: pin() }],
    counts: { added: 0, changed: 1, unchanged: 0 },
  }) as unknown as VisitCheckpoint;
describe("visit checkpoint exact response boundaries", () => {
  it("disables artifact preview when current original hash contradicts the exact reference", () => {
    const state = {
      ...e,
      artifacts: [
        { id: "A", version: 2, status: "AVAILABLE", sha256: "a".repeat(64) },
      ],
    } as Engagement;
    const ref = pin().reference as Parameters<typeof checkpointRecord>[1];
    expect(checkpointRecord(state, ref)?.id).toBe("A");
    expect(
      checkpointRecord(state, { ...ref, sha256: "c".repeat(64) }),
    ).toBeNull();
    expect(checkpointRecord(state, { ...ref, version: 3 })).toBeNull();
    expect(
      checkpointRecord(
        {
          ...state,
          artifacts: [{ ...state.artifacts[0], status: "QUARANTINED" }],
        },
        ref,
      ),
    ).toBeNull();
  });

  it("matches artifact identity across native version changes but preserves workpaper version identity", () => {
    expect(
      verifyCheckpoint(comparison(), e, true).changes?.[0].current.reference
        .version,
    ).toBe(2);
    const value = comparison();
    value.changes![0].current.reference.kind = "workpaper";
    value.changes![0].prior!.reference.kind = "workpaper";
    expect(() => verifyCheckpoint(value, e, true)).toThrow();
  });
  it.each([
    "CONTEXT_CHANGED",
    "TARGET_UNAVAILABLE",
    "INPUT_LIMIT_EXCEEDED",
    "INPUT_DATA_UNAVAILABLE",
  ])("rejects inventory on redacted %s", (status) => {
    expect(() =>
      verifyCheckpoint({ ...comparison(), status }, e, true),
    ).toThrow();
    expect(
      verifyCheckpoint({ ...base(), status }, e, true).counts,
    ).toBeUndefined();
  });
  it("rejects comparison rows supplied by metadata or capture endpoints", () => {
    expect(() => verifyCheckpoint(comparison(), e)).toThrow();
    expect(() =>
      verifyCheckpoint(
        { ...base(), counts: { added: 0, changed: 0, unchanged: 9 } },
        e,
      ),
    ).toThrow();
  });
  it("rejects stale or foreign workspace responses and dishonest counts", () => {
    for (const patch of [
      { engagement_id: "OTHER" },
      { current_engagement_revision: 3 },
      { formal_work_mutated: true },
      { version: true },
    ])
      expect(() =>
        verifyCheckpoint({ ...base(), ...patch } as VisitCheckpoint, e),
      ).toThrow();
    expect(() =>
      verifyCheckpoint(
        { ...comparison(), counts: { added: 1, changed: 0, unchanged: 0 } },
        e,
        true,
      ),
    ).toThrow();
  });
  it("rejects duplicate same-record rows even when artifact versions differ", () => {
    const value = comparison();
    value.changes!.push({
      ...value.changes![0],
      current: pin("artifact", 3),
    } as never);
    value.counts!.changed = 2;
    expect(() => verifyCheckpoint(value, e, true)).toThrow();
  });
  it("rejects missing typed pins, malformed hashes and oversized inventory", () => {
    const value = comparison();
    value.changes![0].current.record_sha256 = "wrong";
    expect(() => verifyCheckpoint(value, e, true)).toThrow();
    expect(() =>
      verifyCheckpoint(
        {
          ...comparison(),
          changes: Array(10001).fill(comparison().changes![0]),
        },
        e,
        true,
      ),
    ).toThrow();
  });
});
