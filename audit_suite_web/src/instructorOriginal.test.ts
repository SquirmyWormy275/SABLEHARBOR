import { expect, it, vi, afterEach } from "vitest";
import {
  KEY_ORIGINAL_LIMIT,
  loadInstructorOriginal,
  originalKeyOptions,
  verifyInstructorOriginal,
  type InstructorOriginal,
} from "./instructorOriginal";
import type { KeyEntry } from "./instructorKey";
const text = '\ufeff{\n  "label": "雪", "label": "preserved duplicate"\n}\n';
const bytes = new TextEncoder().encode(text);
const sha = Array.from(
  new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
  (b) => b.toString(16).padStart(2, "0"),
).join("");
const entry: KeyEntry = {
  id: "MM-01.01.V01",
  raw_sha256: sha,
  canonical_sha256: "a".repeat(64),
  key_sha256: "b".repeat(64),
  review: {
    professional: "UNVALIDATED",
    causal_validation: "NOT_RUN",
    grading: "NOT_RUN",
    gaps: [],
  },
};
const archive = "c".repeat(64);
const value = (): InstructorOriginal => ({
  status: "UNBOUND_REFERENCE_LIBRARY",
  binding: { status: "NOT_BOUND", engagement_id: "ENG-1" },
  archive: { sha256: archive },
  scenario_id: entry.id,
  key_sha256: entry.key_sha256,
  raw_sha256: sha,
  canonical_sha256: entry.canonical_sha256,
  byte_count: bytes.length,
  encoding: "base64",
  content_base64: btoa(String.fromCharCode(...bytes)),
  media_type: "application/json",
});
afterEach(() => vi.unstubAllGlobals());
it("preserves exact noncanonical text, Unicode and BOM after byte hashing", async () => {
  expect(await verifyInstructorOriginal(value(), entry, "ENG-1", archive)).toBe(
    text,
  );
});
it("rejects mismatched authority and source pins", async () => {
  for (const patch of [
    { archive: { sha256: "d".repeat(64) } },
    { binding: { status: "NOT_BOUND", engagement_id: "ENG-OTHER" } },
    { scenario_id: "MM-02" },
    { key_sha256: "d".repeat(64) },
    { raw_sha256: "d".repeat(64) },
    { canonical_sha256: "d".repeat(64) },
    { encoding: "utf8" },
    { media_type: "text/html" },
  ])
    await expect(
      verifyInstructorOriginal(
        { ...value(), ...patch } as InstructorOriginal,
        entry,
        "ENG-1",
        archive,
      ),
    ).rejects.toThrow();
});
it("rejects corrupt bytes and malformed or noncanonical base64", async () => {
  for (const encoded of [
    value().content_base64.replace(/^./, "A"),
    " ".repeat(value().content_base64.length),
    "Zh==",
  ])
    await expect(
      verifyInstructorOriginal(
        {
          ...value(),
          content_base64: encoded,
          byte_count: encoded === "Zh==" ? 1 : bytes.length,
        },
        entry,
        "ENG-1",
        archive,
      ),
    ).rejects.toThrow();
});
it("rejects invalid sizes before decoding", async () => {
  for (const byte_count of [-1, 1.5, KEY_ORIGINAL_LIMIT + 1, Number.NaN])
    await expect(
      verifyInstructorOriginal(
        { ...value(), byte_count },
        entry,
        "ENG-1",
        archive,
      ),
    ).rejects.toThrow();
});
it("bounds choices and retains an explicit selection outside search", () => {
  const entries = Array.from({ length: 1110 }, (_, i) => ({
    ...entry,
    id: `SOURCE-${i}`,
  }));
  const all = originalKeyOptions(entries, "", "SOURCE-1000");
  expect(all.total).toBe(1110);
  expect(all.options).toHaveLength(51);
  expect(all.options[0].id).toBe("SOURCE-1000");
  const filtered = originalKeyOptions(entries, " source-999 ", "SOURCE-1000");
  expect(filtered.total).toBe(1);
  expect(filtered.options.map((e) => e.id)).toEqual([
    "SOURCE-1000",
    "SOURCE-999",
  ]);
});
it("loads only an explicit same-origin no-store request", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify(value())));
  vi.stubGlobal("fetch", fetcher);
  expect(
    (
      await loadInstructorOriginal(
        entry,
        "ENG-1",
        archive,
        new AbortController().signal,
      )
    ).text,
  ).toBe(text);
  expect(fetcher).toHaveBeenCalledWith(
    expect.stringContaining(`/instructor-key/${entry.id}/original`),
    expect.objectContaining({ credentials: "same-origin", cache: "no-store" }),
  );
});
it("bounds streamed responses without trusting content length", async () => {
  let cancelled = false;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        new ReadableStream({
          start(c) {
            c.enqueue(new Uint8Array(6 * 1024 * 1024 + 1));
          },
          cancel() {
            cancelled = true;
          },
        }),
      ),
    ),
  );
  await expect(
    loadInstructorOriginal(
      entry,
      "ENG-1",
      archive,
      new AbortController().signal,
    ),
  ).rejects.toThrow("limit");
  expect(cancelled).toBe(true);
});
it("rejects revoked and aborted requests without showing bytes", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response("denied", { status: 403 })),
  );
  await expect(
    loadInstructorOriginal(
      entry,
      "ENG-1",
      archive,
      new AbortController().signal,
    ),
  ).rejects.toThrow("unavailable");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(value()))),
  );
  const c = new AbortController();
  c.abort();
  await expect(
    loadInstructorOriginal(entry, "ENG-1", archive, c.signal),
  ).rejects.toThrow("cancelled");
});
