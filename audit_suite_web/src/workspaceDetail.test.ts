import { afterEach, expect, test, vi } from "vitest";
import { command, normalize, request, type Engagement, type Row } from "./api";
import {
  deferredPaper,
  deferredTrace,
  loadSampleOriginalContext,
  loadWorkspaceDetail,
  mergeWorkspaceRecord,
} from "./workspaceDetail";
import { sampleOriginalContext } from "./sampleOriginalObservations";

afterEach(() => vi.unstubAllGlobals());
async function fixture() {
  const text = "Exact 🧭 historical quote",
    bytes = new TextEncoder().encode(text);
  const sha = Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    (x) => x.toString(16).padStart(2, "0"),
  ).join("");
  const pin = {
    schema: "SH_WORKSPACE_SUMMARY_V1",
    engagement_id: "ENG-1",
    engagement_revision: 3,
    source_epoch_sha256: "a".repeat(64),
    collection: "workpapers",
    object_id: "WP-1",
    object_sha256: "b".repeat(64),
  };
  const first = {
    version: 1,
    _workspace_version_sha256: "c".repeat(64),
    _workspace_text: {
      loaded: false,
      bytes: bytes.length,
      characters: Array.from(text).length,
      sha256: sha,
    },
  };
  const second = {
    ...first,
    version: 2,
    _workspace_version_sha256: "d".repeat(64),
  };
  const row: Row = {
    id: "WP-1",
    versions: [first, second],
    _workspace_detail: pin,
  };
  const e = normalize({
    id: "ENG-1",
    revision: 3,
    permissions: ["learn"],
    scope: { boundaries: ["B"] },
    workspace_transport: {
      schema: pin.schema,
      source_epoch_sha256: pin.source_epoch_sha256,
    },
    workpapers: [row],
    artifacts: [{ id: "ART-1", status: "AVAILABLE", sha256: "e".repeat(64) }],
  } as unknown as Engagement);
  const full: Row = {
    ...row,
    versions: [
      {
        ...first,
        text,
        _workspace_text: { ...first._workspace_text, loaded: true },
      },
      second,
    ],
  };
  return { e, row, pin, full, text };
}
function reply(value: unknown) {
  const fetcher = vi.fn(
    async (_path: string, _options?: RequestInit) =>
      new Response(JSON.stringify(value), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
  );
  vi.stubGlobal("fetch", fetcher);
  return fetcher;
}

test("browser engagement reads and command responses request summaries without changing scoped URLs", async () => {
  const fetcher = reply({ id: "ENG-1", revision: 3 });
  await request("/api/engagements/ENG-1");
  await command("ENG-1", 3, "note.create", { text: "Note" });
  expect(fetcher.mock.calls.map(([path]) => path)).toEqual([
    "/api/engagements/ENG-1",
    "/api/engagements/ENG-1/commands",
  ]);
  for (const call of fetcher.mock.calls)
    expect((call as unknown as [string, RequestInit])[1].headers).toMatchObject(
      { "X-Workspace-View": "summary-v1" },
    );
});

test("exact historical text is byte checked and a later version stays explicitly deferred", async () => {
  const f = await fixture(),
    fetcher = reply({ context: f.pin, row: f.full });
  expect(deferredPaper(f.row, 1)).toBe(true);
  const loaded = await loadWorkspaceDetail(f.e, "workpapers", f.row, 1);
  expect(deferredPaper(loaded, 1)).toBe(false);
  expect(deferredPaper(loaded, 2)).toBe(true);
  expect((loaded.versions as Row[])[0].text).toBe(f.text);
  expect(String(fetcher.mock.calls[0][0])).toContain("version=1");
  expect(String(fetcher.mock.calls[0][0])).toContain("observed_revision=3");
  expect((f.row.versions as Row[])[0]).not.toHaveProperty("text");
});

test("altered body with the same declared text pins is refused", async () => {
  const f = await fixture(),
    bad = structuredClone(f.full);
  (bad.versions as Row[])[0].text = f.text.replace("Exact", "Wrong");
  reply({ context: f.pin, row: bad });
  await expect(
    loadWorkspaceDetail(f.e, "workpapers", f.row, 1),
  ).rejects.toThrow("exact byte check");
});

test("foreign or stale response context is refused before hydration", async () => {
  const f = await fixture();
  reply({ context: { ...f.pin, engagement_revision: 4 }, row: f.full });
  await expect(
    loadWorkspaceDetail(f.e, "workpapers", f.row, 1),
  ).rejects.toThrow("workspace or object pins");
  const fetcher = reply({});
  await expect(
    loadWorkspaceDetail({ ...f.e, id: "ENG-OTHER" }, "workpapers", f.row, 1),
  ).rejects.toThrow("current workspace");
  expect(fetcher).not.toHaveBeenCalled();
});

test("local version hydration merges only within the exact same epoch and engagement", async () => {
  const f = await fixture(),
    next = structuredClone(f.row),
    originalVersions = f.full.versions as Row[];
  (next.versions as Row[])[1] = {
    ...originalVersions[1],
    text: f.text,
    _workspace_text: {
      ...(originalVersions[1]._workspace_text as object),
      loaded: true,
    },
  };
  const merged = mergeWorkspaceRecord(f.full, next);
  expect(deferredPaper(merged, 1)).toBe(false);
  expect(deferredPaper(merged, 2)).toBe(false);
  const foreign = {
    ...next,
    _workspace_detail: { ...f.pin, engagement_id: "ENG-OTHER" },
  };
  expect(deferredPaper(mergeWorkspaceRecord(f.full, foreign), 1)).toBe(true);
});

test("unloaded sample observations are distinct from a complete empty citation result", async () => {
  const f = await fixture();
  f.e.sample_executions = [
    {
      id: "TRACE-1",
      revision: 1,
      _workspace_items: { loaded: false, count: 4 },
    },
  ];
  expect(deferredTrace((f.e.sample_executions as Row[])[0])).toBe(true);
  expect(sampleOriginalContext(f.e, "ART-1")).toEqual({
    rows: [],
    unavailable: false,
    deferred: true,
  });
  f.e.sample_executions = [];
  expect(sampleOriginalContext(f.e, "ART-1")).toEqual({
    rows: [],
    unavailable: false,
  });
});

test("sample-original context accepts only complete current membership and exact artifact hash", async () => {
  const f = await fixture();
  f.e.sample_executions = [
    { id: "TRACE-1", revision: 1, workpaper_digest: "v" },
  ];
  const value = {
    engagement_id: f.e.id,
    engagement_revision: 3,
    source_epoch_sha256: f.pin.source_epoch_sha256,
    artifact_id: "ART-1",
    artifact_sha256: "e".repeat(64),
    complete_exact_original_selection: true,
    retained_trace_count: 1,
    traces: [{ id: "TRACE-1", revision: 1, workpaper_digest: "v", items: [] }],
  };
  reply(value);
  expect(await loadSampleOriginalContext(f.e, "ART-1")).toEqual(value.traces);
  reply({ ...value, complete_exact_original_selection: 1 });
  await expect(loadSampleOriginalContext(f.e, "ART-1")).rejects.toThrow(
    "workspace pins",
  );
  reply({ ...value, artifact_sha256: "f".repeat(64) });
  await expect(loadSampleOriginalContext(f.e, "ART-1")).rejects.toThrow(
    "workspace pins",
  );
  reply({ ...value, traces: [{ ...value.traces[0], revision: 2 }] });
  await expect(loadSampleOriginalContext(f.e, "ART-1")).rejects.toThrow(
    "membership",
  );
});
