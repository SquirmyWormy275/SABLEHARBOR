import { afterEach, expect, it, vi } from "vitest";
import { requestDownload, setCSRF, ApiError } from "./api";
afterEach(() => vi.unstubAllGlobals());
const bytes = new TextEncoder().encode("fixture archive");
async function pins() {
  return {
    sha256: Array.from(
      new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    )
      .map((n) => n.toString(16).padStart(2, "0"))
      .join(""),
    bytes: bytes.length,
    maxBytes: 1024,
  };
}
it("POSTs CSRF and verifies bytes before returning blob", async () => {
  const p = await pins();
  setCSRF("fixture");
  const f = vi.fn(
    async () =>
      new Response(bytes, {
        headers: {
          "content-type": "application/zip",
          "x-content-sha256": p.sha256,
        },
      }),
  );
  vi.stubGlobal("fetch", f);
  expect(
    await (await requestDownload("/export", { command_id: "C" }, p)).text(),
  ).toBe("fixture archive");
  expect(f.mock.calls[0]).toEqual([
    "/export",
    expect.objectContaining({
      method: "POST",
      credentials: "same-origin",
      headers: expect.objectContaining({ "X-CSRF-Token": "fixture" }),
    }),
  ]);
});
it("rejects oversized/truncated/corrupt/mismatched exports", async () => {
  const p = await pins();
  for (const raw of [
    "short",
    "x".repeat(bytes.length + 1),
    "x".repeat(bytes.length),
  ]) {
    vi.stubGlobal(
      "fetch",
      async () =>
        new Response(raw, {
          headers: {
            "content-type": "application/zip",
            "x-content-sha256": p.sha256,
          },
        }),
    );
    await expect(requestDownload("/export", {}, p)).rejects.toThrow();
  }
  vi.stubGlobal(
    "fetch",
    async () =>
      new Response(bytes, {
        headers: {
          "content-type": "application/zip",
          "x-content-sha256": "a".repeat(64),
        },
      }),
  );
  await expect(requestDownload("/export", {}, p)).rejects.toThrow(
    "exact preview",
  );
});
it("retains auth failure status and rejects unbounded previews before fetch", async () => {
  const f = vi.fn(
    async () =>
      new Response(JSON.stringify({ error: "Revoked" }), { status: 403 }),
  );
  vi.stubGlobal("fetch", f);
  await expect(
    requestDownload("/export", {}, await pins()),
  ).rejects.toBeInstanceOf(ApiError);
  f.mockClear();
  await expect(
    requestDownload("/export", {}, { ...(await pins()), maxBytes: Infinity }),
  ).rejects.toThrow();
  expect(f).not.toHaveBeenCalled();
});
