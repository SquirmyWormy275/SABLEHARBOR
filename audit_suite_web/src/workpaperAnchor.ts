export const ANCHOR_FIELDS = [
  "text",
  "objective",
  "procedures",
  "conclusion",
] as const;
export type PassageAnchor = {
  field: (typeof ANCHOR_FIELDS)[number];
  start: number;
  end: number;
  excerpt: string;
};
export type AnchorVersion = Record<string, unknown>;
export function scalarText(text: string): boolean {
  return !Array.from(text).some(
    (c) =>
      c.length === 1 && c.charCodeAt(0) >= 0xd800 && c.charCodeAt(0) <= 0xdfff,
  );
}
export function validAnchor(
  value: unknown,
  version: AnchorVersion,
): value is PassageAnchor {
  if (!value || typeof value !== "object") return false;
  const a = value as PassageAnchor;
  if (
    Object.keys(a).sort().join() !== "end,excerpt,field,start" ||
    !ANCHOR_FIELDS.includes(a.field)
  )
    return false;
  const text = version[a.field];
  return (
    typeof text === "string" &&
    scalarText(text) &&
    typeof a.excerpt === "string" &&
    scalarText(a.excerpt) &&
    Number.isSafeInteger(a.start) &&
    Number.isSafeInteger(a.end) &&
    a.start >= 0 &&
    a.end > a.start &&
    a.end <= Array.from(text).length &&
    Array.from(a.excerpt).length <= 4000 &&
    Array.from(text).slice(a.start, a.end).join("") === a.excerpt
  );
}
export function selectedAnchor(
  version: AnchorVersion,
  field: PassageAnchor["field"],
  start: number,
  end: number,
): PassageAnchor | null {
  const text = version[field];
  if (
    typeof text !== "string" ||
    !scalarText(text) ||
    !Number.isSafeInteger(start) ||
    !Number.isSafeInteger(end) ||
    start < 0 ||
    end > text.length ||
    start >= end
  )
    return null;
  const split = (n: number) =>
    n > 0 &&
    n < text.length &&
    /[\uD800-\uDBFF]/.test(text[n - 1]) &&
    /[\uDC00-\uDFFF]/.test(text[n]);
  if (split(start) || split(end)) return null;
  const a = {
    field,
    start: Array.from(text.slice(0, start)).length,
    end: Array.from(text.slice(0, end)).length,
    excerpt: text.slice(start, end),
  };
  return validAnchor(a, version) ? a : null;
}
export function recordedAnchor(review: AnchorVersion): PassageAnchor | null {
  const a = review.anchor as Record<string, unknown> | undefined;
  if (
    !a ||
    Object.keys(a).sort().join() !== "end,excerpt,field,offset_unit,start" ||
    a.offset_unit !== "UNICODE_CODEPOINT" ||
    !Number.isSafeInteger(review.workpaper_version) ||
    Number(review.workpaper_version) < 1 ||
    typeof review.workpaper_version_digest !== "string" ||
    !/^[a-f0-9]{64}$/.test(review.workpaper_version_digest)
  )
    return null;
  const { offset_unit: _unit, ...request } = a;
  if (
    typeof request.excerpt !== "string" ||
    !scalarText(request.excerpt) ||
    !Number.isSafeInteger(request.start) ||
    Number(request.start) < 0
  )
    return null;
  // Validate the stored shape without looking up or substituting a current version.
  const n = Array.from(request.excerpt).length;
  if (
    !ANCHOR_FIELDS.includes(request.field as PassageAnchor["field"]) ||
    !n ||
    n > 4000 ||
    !Number.isSafeInteger(request.end) ||
    Number(request.end) - Number(request.start) !== n
  )
    return null;
  return request as PassageAnchor;
}
