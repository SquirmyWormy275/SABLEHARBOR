import { describe, expect, it } from "vitest";
import type { Engagement } from "./api";
import type { BoundSource } from "./boundInstructorKey";
import { boundRetainedArtifacts } from "./boundRetainedSources";
const source = {
  id: "S",
  company: "CO",
  branch: "B",
  system: "SYS",
  record: "R",
  version: 1,
  sha256: "a".repeat(64),
  source_store_id: "store",
  source_system_alias: "alias:SYS",
  registry_sha256: "b".repeat(64),
  retained_audit_artifact_ids: ["A"],
  actor_granted_at_binding: false,
} as BoundSource;
const artifact = {
  id: "A",
  engagement_id: "E",
  status: "AVAILABLE",
  sha256: source.sha256,
  version: 1,
  source: {
    kind: "COLLECTED_COMPANY_SOURCE",
    receipt: {
      engagement_id: "E",
      source: {
        company: source.company,
        branch: source.branch,
        system: source.system,
        record: source.record,
        version: source.version,
        sha256: source.sha256,
        source_store_id: source.source_store_id,
        source_system_alias: source.source_system_alias,
        registry_sha256: source.registry_sha256,
      },
    },
  },
};
const e = {
  id: "E",
  permissions: ["instruct"],
  artifacts: [artifact],
} as unknown as Engagement;
describe("protected exact retained originals", () => {
  it("opens exact current audit copy independently of historical native grant", () =>
    expect(boundRetainedArtifacts(e, source)).toEqual([artifact]));
  it("denies learner access, missing listed IDs, ambiguous copies and quarantine", () => {
    expect(
      boundRetainedArtifacts({ ...e, permissions: ["learn"] }, source),
    ).toEqual([]);
    expect(
      boundRetainedArtifacts(e, {
        ...source,
        retained_audit_artifact_ids: ["OTHER"],
      }),
    ).toEqual([]);
    expect(
      boundRetainedArtifacts({ ...e, artifacts: [artifact, artifact] }, source),
    ).toEqual([]);
    expect(
      boundRetainedArtifacts(
        { ...e, artifacts: [{ ...artifact, status: "QUARANTINED" }] },
        source,
      ),
    ).toEqual([]);
  });
  it("rejects changed versions, SHA, source identity and cross-engagement receipts", () => {
    for (const changed of [
      { version: 2 },
      { sha256: "c".repeat(64) },
      { branch: "OTHER" },
      { company: "OTHER" },
      { record: "OTHER" },
    ])
      expect(boundRetainedArtifacts(e, { ...source, ...changed })).toEqual([]);
    expect(boundRetainedArtifacts({ ...e, id: "OTHER" }, source)).toEqual([]);
  });
  it("rejects incomplete or changed physical routing, without latest fallback", () => {
    for (const changed of [
      { source_store_id: undefined },
      { source_system_alias: "OTHER" },
      { registry_sha256: "c".repeat(64) },
    ])
      expect(boundRetainedArtifacts(e, { ...source, ...changed })).toEqual([]);
  });
});
