import { expect, it, vi } from "vitest";
import type { Engagement, Row } from "./api";
import {
  acceptsComparison,
  comparisonArtifact,
  comparisonOptions,
  comparisonContext,
  comparisonPin,
  originalIdentity,
} from "./originalComparison";
import { loadTextPreview } from "./workpaperSupport";
const artifact: Row = {
  id: "A",
  status: "AVAILABLE",
  sha256: "a".repeat(64),
  bytes: 1,
  mime: "text/plain",
};
const fixture = () =>
  ({
    id: "E",
    revision: 1,
    permissions: ["learn"],
    scope: { boundaries: ["corporate"] },
    artifacts: [artifact],
    company_source_binding: { branch: "A" },
    evidence_acquisition: { mode: "source" },
  }) as unknown as Engagement;
it("pins exact source, scope, authority, version and both success/error response context", () => {
  const e = fixture(),
    pin = comparisonPin(e, "USER", "A");
  expect(acceptsComparison(pin, e, "USER", "A")).toBe(true);
  for (const change of [
    { revision: 2 },
    { scope: { boundaries: ["other"] } },
    { company_source_binding: { branch: "B" } },
    { evidence_acquisition: { mode: "other" } },
    { permissions: ["review"] },
    {
      artifacts: [
        { ...artifact, source: { receipt: { source: { version: 2 } } } },
      ],
    },
  ])
    expect(
      acceptsComparison(pin, { ...e, ...change } as Engagement, "USER", "A"),
    ).toBe(false);
  expect(acceptsComparison(pin, e, "OTHER", "A")).toBe(false);
  expect(comparisonContext({ ...e, revision: 2 }, "USER")).toBe(
    comparisonContext(e, "USER"),
  );
});
it("rejects ambiguous/unavailable/cross-engagement originals and labels partial routes", () => {
  const e = fixture();
  expect(
    comparisonArtifact({ ...e, artifacts: [artifact, artifact] }, "A"),
  ).toBeUndefined();
  for (const update of [
    { status: "WITHHELD" },
    { engagement_id: "OTHER" },
    { sha256: "invalid" },
  ])
    expect(
      comparisonArtifact(
        { ...e, artifacts: [{ ...artifact, ...update }] },
        "A",
      ),
    ).toBeUndefined();
  expect(
    originalIdentity({
      ...artifact,
      source: { receipt: { source: { source_system_alias: "STORE:old" } } },
    }).routeStatus,
  ).toContain("Incomplete");
});
it("checks actual exact bytes, failed UTF8, denied response and bounded stream independently", async () => {
  const bytes = new Uint8Array([0xff]);
  const hash = Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    (b) => b.toString(16).padStart(2, "0"),
  ).join("");
  const mock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(bytes))
    .mockResolvedValueOnce(new Response("denied", { status: 403 }))
    .mockResolvedValueOnce(new Response("too long"));
  try {
    await expect(
      loadTextPreview(
        "E",
        { ...artifact, sha256: hash },
        new AbortController().signal,
      ),
    ).rejects.toThrow();
    await expect(
      loadTextPreview("E", artifact, new AbortController().signal),
    ).rejects.toThrow("403");
    await expect(
      loadTextPreview("E", artifact, new AbortController().signal),
    ).rejects.toThrow("hash");
  } finally {
    mock.mockRestore();
  }
});

it("bounds search and preserves an exact selected historical original outside results", () => {
  const e = fixture();
  e.artifacts = [
    ...Array.from({ length: 70 }, (_, i) => ({
      ...artifact,
      id: `FILE-${i}`,
      name: `File ${i}`,
    })),
    {
      ...artifact,
      id: "OLD",
      source: {
        receipt: {
          source: {
            system: "native",
            record: "old",
            version: 1,
            source_system_alias: "ARCHIVE:only",
          },
        },
      },
    },
  ];
  const options = comparisonOptions(e, "File", "OLD");
  expect(options.total).toBe(70);
  expect(options.options).toHaveLength(51);
  expect(options.options[0].id).toBe("OLD");
  expect(
    comparisonOptions(e, "ARCHIVE:only", "").options.map((a) => a.id),
  ).toEqual(["OLD"]);
  e.artifacts.push({ ...e.artifacts.at(-1)!, status: "WITHHELD" });
  expect(comparisonOptions(e, "ARCHIVE:only", "OLD").options).toEqual([]);
});
