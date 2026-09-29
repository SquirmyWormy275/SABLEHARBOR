import { afterEach, describe, it, expect, vi } from "vitest";
import { request, setCSRF, command, artifactURL } from "./api";
afterEach(() => vi.unstubAllGlobals());
describe("authenticated service boundary", () => {
  it("sends cookies, CSRF, revision and command identity without caller roles", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "e", revision: 3 })),
      );
    vi.stubGlobal("fetch", fetcher);
    setCSRF("fixture-csrf");
    await command("e", 2, "note.create", { text: "Evidence follow-up" });
    const [url, opts] = fetcher.mock.calls[0];
    expect(url).toBe("/api/engagements/e/commands");
    expect(opts.credentials).toBe("same-origin");
    expect(opts.headers["X-CSRF-Token"]).toBe("fixture-csrf");
    expect(JSON.parse(opts.body)).toEqual({
      command_id: expect.any(String),
      expected_revision: 2,
      kind: "note.create",
      payload: { text: "Evidence follow-up" },
    });
  });
  it("does not manufacture success on stale revisions or malformed responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "Revision conflict" }), {
          status: 409,
        }),
      ),
    );
    await expect(request("/api/test", "POST", {})).rejects.toMatchObject({
      status: 409,
      message: "Revision conflict",
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not JSON")));
    await expect(request("/api/test")).rejects.toThrow("unreadable");
  });
  it("encodes artifact path segments", () =>
    expect(artifactURL("a/b", "c?d")).toBe(
      "/api/engagements/a%2Fb/artifacts/c%3Fd/download",
    ));
});

describe("retained workpaper review actions", () => {
  it("creates a successor payload without modifying predecessor evidence", async () => {
    const { newWorkpaperVersion, workpaperVersions } = await import("./api");
    const paper = {
      id: "WP1",
      prepared_by: "P1",
      versions: [
        {
          version: 1,
          objective: "Compare",
          procedures: "Inspect",
          evidence_ids: ["A1", "A2"],
          conclusion: "LIMITATION",
        },
      ],
    };
    const before = JSON.stringify(paper);
    const payload = newWorkpaperVersion(paper);
    expect(payload).toMatchObject({
      workpaper_id: "WP1",
      evidence_ids: "A1, A2",
      conclusion: "LIMITATION",
    });
    expect(workpaperVersions(paper)[0]).toMatchObject({
      id: "WP1:v1",
      version: 1,
    });
    expect(JSON.stringify(paper)).toBe(before);
  });
  it("requires actual review membership and a distinct preparer", async () => {
    const { canReviewWorkpaper } = await import("./api");
    const paper = { id: "WP1", prepared_by: "P1" };
    expect(canReviewWorkpaper(paper, "P1", ["instruct"])).toBe(false);
    expect(canReviewWorkpaper(paper, "P2", ["learn"])).toBe(false);
    expect(canReviewWorkpaper(paper, undefined, ["review"])).toBe(false);
    expect(canReviewWorkpaper(paper, "P2", ["review"])).toBe(true);
    expect(canReviewWorkpaper(paper, "P2", ["instruct"])).toBe(true);
  });
});

it("counts actual received artifacts independently of later clarification status", async () => {
  const { requestHasDelivery } = await import("./api");
  expect(
    requestHasDelivery({ id: "P1", status: "DELIVERED", artifact_ids: ["A1"] }),
  ).toBe(true);
  expect(
    requestHasDelivery({
      id: "P1",
      status: "CLARIFICATION",
      artifact_ids: ["A1"],
    }),
  ).toBe(true);
  expect(
    requestHasDelivery({ id: "P2", status: "SUBMITTED", artifact_ids: [] }),
  ).toBe(false);
  expect(requestHasDelivery({ id: "P3", status: "DRAFT" })).toBe(false);
});

it("blocks independent review of a successor authored by the reviewer", async () => {
  const { canReviewWorkpaper } = await import("./api");
  expect(
    canReviewWorkpaper({ id: "WP1", prepared_by: "P1" }, "P2", ["instruct"], {
      id: "WP1:v2",
      actor: "P2",
    }),
  ).toBe(false);
});
