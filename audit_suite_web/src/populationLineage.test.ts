import { describe, it, expect } from "vitest";
import type { Engagement } from "./api";
import { populationLineage, lineageReference } from "./populationLineage";
const artifact = { id: "A", sha256: "a".repeat(64), status: "AVAILABLE" },
  manifest = { id: "M", sha256: "b".repeat(64), status: "AVAILABLE" };
const pop = {
  id: "P",
  version: 1,
  status: "PROVISIONAL",
  artifact_id: "A",
  immutable: {
    source_json: JSON.stringify({
      original_sha256: artifact.sha256,
      query_manifest_artifact_id: "M",
      query_manifest_sha256: manifest.sha256,
    }),
  },
};
const sel = { id: "S", population_id: "P", population_version: 1 };
const e = {
  populations: [pop],
  selections: [sel],
  artifacts: [artifact, manifest],
  workpapers: [
    {
      id: "W",
      control_id: "C",
      versions: [
        { id: "V1", version: 1, evidence_ids: ["A"] },
        { id: "V2", version: 2, evidence_ids: [] },
      ],
    },
    {
      id: "UNRELATED",
      control_id: "C",
      title: "Same population",
      versions: [{ id: "V", version: 1, evidence_ids: [] }],
    },
  ],
} as unknown as Engagement;
describe("exact population/selection lineage", () => {
  it("traces exact population, original, manifest and explicitly linked workpaper version", () => {
    const result = populationLineage(e, "selection", sel);
    expect(result.links.map((l) => l.reference.collection)).toEqual([
      "populations",
      "artifacts",
      "artifacts",
      "workpapers",
    ]);
    expect(result.links.at(-1)?.reference).toMatchObject({
      id: "W",
      version: 1,
    });
    expect(result.workpaperLinks).toBe(1);
  });
  it("does not substitute a newer population or workpaper version", () => {
    expect(
      populationLineage(e, "selection", { ...sel, population_version: 2 })
        .links,
    ).toEqual([]);
    expect(
      lineageReference(e, { id: "W", collection: "workpapers", version: 3 }),
    ).toBeNull();
  });
  it("withholds originals/manifests with changed hashes or unavailable bytes", () => {
    const changed = {
      ...e,
      artifacts: [
        { ...artifact, sha256: "c".repeat(64) },
        { ...manifest, status: "QUARANTINED" },
      ],
    };
    const result = populationLineage(changed, "selection", sel);
    expect(result.links.map((l) => l.reference.collection)).toEqual([
      "populations",
    ]);
    expect(result.workpaperLinks).toBe(0);
    expect(result.unavailable).toHaveLength(2);
  });
  it("does not infer links by control/title and handles missing source pins", () => {
    expect(
      populationLineage(
        { ...e, workpapers: [e.workpapers[1]] },
        "population",
        pop,
      ).workpaperLinks,
    ).toBe(0);
    const legacy = { ...pop, immutable: { source_json: "not-json" } };
    expect(
      populationLineage(
        { ...e, populations: [legacy] },
        "population",
        legacy,
      ).links.map((l) => l.reference.collection),
    ).toEqual(["selections"]);
  });
});
