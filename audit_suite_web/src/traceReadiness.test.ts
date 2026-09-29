import { describe, expect, it } from "vitest";
import type { Engagement } from "./api";
import type { ContextLink } from "./investigationContext";
import {
  resolveTraceReference,
  tracePosition,
  visibleCount,
  type TraceReadiness,
} from "./traceReadiness";
const pin: ContextLink = {
  kind: "workpaper",
  id: "W",
  version: 1,
  sha256: "a".repeat(64),
};
function state() {
  return {
    id: "E",
    revision: 7,
    workpapers: [
      {
        id: "W",
        version: 2,
        versions: [
          { version: 1, text: "Earlier" },
          { version: 2, text: "Later" },
        ],
      },
    ],
    artifacts: [],
    tasks: [],
    populations: [],
    selections: [],
    controls: [],
    sample_execution_inputs: {
      status: "AVAILABLE",
      engagement_id: "E",
      engagement_revision: 7,
      workpaper_versions: [
        {
          workpaper_id: "W",
          workpaper_version: 1,
          workpaper_digest: pin.sha256,
        },
      ],
    },
  } as unknown as Engagement;
}
describe("procedure trace navigation", () => {
  it("resolves an exact historical version without selecting the current version", () => {
    expect(resolveTraceReference(state(), pin)?.version).toBe(2);
    expect(pin.version).toBe(1);
    expect(resolveTraceReference(state(), { ...pin, version: 3 })).toBeNull();
  });
  it("rejects wrong digest, stale revision and unavailable input metadata", () => {
    expect(
      resolveTraceReference(state(), { ...pin, sha256: "b".repeat(64) }),
    ).toBeNull();
    const e = state();
    e.revision = 8;
    expect(resolveTraceReference(e, pin)).toBeNull();
    e.revision = 7;
    (e.sample_execution_inputs as Record<string, unknown>).status =
      "INPUT_LIMIT_EXCEEDED";
    expect(resolveTraceReference(e, pin)).toBeNull();
  });
  it("rejects duplicate projected identities and duplicate historical versions", () => {
    const e = state();
    e.workpapers.push(structuredClone(e.workpapers[0]));
    expect(resolveTraceReference(e, pin)).toBeNull();
    e.workpapers.pop();
    (e.workpapers[0].versions as { version: number }[]).push({ version: 1 });
    expect(resolveTraceReference(e, pin)).toBeNull();
  });
  it("requires actual retained artifact status and digest", () => {
    const e = state();
    e.artifacts = [{ id: "A", status: "AVAILABLE", sha256: "a".repeat(64) }];
    (e.sample_execution_inputs as Record<string, unknown>).artifacts = [
      { artifact_id: "A", sha256: "a".repeat(64) },
    ];
    const ref = { ...pin, kind: "artifact" as const, id: "A", version: null };
    expect(resolveTraceReference(e, ref)?.id).toBe("A");
    e.artifacts[0].status = "QUARANTINED";
    expect(resolveTraceReference(e, ref)).toBeNull();
  });
  it("distinguishes null/unavailable counts from measured zero", () => {
    expect(visibleCount(null)).toBe("Unavailable");
    expect(visibleCount(undefined)).toBe("Unavailable");
    expect(visibleCount(-1)).toBe("Unavailable");
    expect(visibleCount(0)).toBe("0");
  });
  it("uses only explicit validated lineage metadata to label current/historical", () => {
    const data = {
      lineages: [
        {
          root_id: "OLD",
          status: "EXACT_VISIBLE_METADATA_LINKS",
          current_leaf_id: "NEW",
          historical_trace_ids: ["OLD"],
        },
      ],
    } as TraceReadiness;
    expect(tracePosition(data, "OLD")).toBe("Historical retained trace");
    expect(tracePosition(data, "NEW")).toBe("Current trace for this lineage");
    expect(tracePosition(data, "UNKNOWN")).toBe(
      "Correction lineage unavailable",
    );
  });
});
