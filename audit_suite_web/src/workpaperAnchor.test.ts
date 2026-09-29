import { it, expect } from "vitest";
import { selectedAnchor, validAnchor, recordedAnchor } from "./workpaperAnchor";
it("converts UTF16 and preserves exact repeated and combining text", () => {
  const v = { text: "A😀 cafe\u0301 repeat repeat" };
  expect(selectedAnchor(v, "text", 1, 3)).toEqual({
    field: "text",
    start: 1,
    end: 2,
    excerpt: "😀",
  });
  expect(selectedAnchor(v, "text", 17, 23)?.start).toBe(16);
  expect(selectedAnchor(v, "text", 3, 9)?.excerpt).toBe(" cafe\u0301");
});
it("rejects split or unpaired surrogates and invalid selections", () => {
  expect(selectedAnchor({ text: "A😀" }, "text", 1, 2)).toBeNull();
  expect(selectedAnchor({ text: "\ud800x" }, "text", 1, 2)).toBeNull();
  expect(selectedAnchor({ text: "x" }, "text", 0.5, 1)).toBeNull();
});
it("never relocates text or accepts extra fields", () => {
  const a = { field: "text", start: 0, end: 1, excerpt: "x" };
  expect(validAnchor(a, { text: "ax" })).toBe(false);
  expect(
    validAnchor({ ...a, offset_unit: "UNICODE_CODEPOINT" }, { text: "x" }),
  ).toBe(false);
});
it("uses retained metadata without any latest-version lookup", () => {
  const r = {
    workpaper_version: 1,
    workpaper_version_digest: "a".repeat(64),
    anchor: {
      field: "text",
      start: 9,
      end: 10,
      excerpt: "😀",
      offset_unit: "UNICODE_CODEPOINT",
    },
  };
  expect(recordedAnchor(r)?.excerpt).toBe("😀");
  expect(recordedAnchor({ ...r, workpaper_version_digest: "bad" })).toBeNull();
  expect(recordedAnchor({ ...r, anchor: { ...r.anchor, end: 11 } })).toBeNull();
});
