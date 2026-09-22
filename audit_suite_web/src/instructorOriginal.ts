import {
  assertKeyContext,
  type KeyContext,
  type KeyEntry,
} from "./instructorKey";
export const KEY_ORIGINAL_LIMIT = 4 * 1024 * 1024;
const RESPONSE_LIMIT = 6 * 1024 * 1024;
export type InstructorOriginal = KeyContext & {
  scenario_id: string;
  key_sha256: string;
  raw_sha256: string;
  canonical_sha256: string;
  byte_count: number;
  encoding: "base64";
  content_base64: string;
  media_type: "application/json";
};
export async function verifyInstructorOriginal(
  value: InstructorOriginal,
  entry: KeyEntry,
  engagementId: string,
  archive: string,
): Promise<string> {
  assertKeyContext(value, engagementId);
  if (
    value.archive.sha256 !== archive ||
    value.scenario_id !== entry.id ||
    value.key_sha256 !== entry.key_sha256 ||
    value.raw_sha256 !== entry.raw_sha256 ||
    value.canonical_sha256 !== entry.canonical_sha256 ||
    value.encoding !== "base64" ||
    value.media_type !== "application/json" ||
    !Number.isSafeInteger(value.byte_count) ||
    value.byte_count < 0 ||
    value.byte_count > KEY_ORIGINAL_LIMIT ||
    typeof value.content_base64 !== "string" ||
    value.content_base64.length !== 4 * Math.ceil(value.byte_count / 3)
  )
    throw Error("Original differs from the selected protected source.");
  const decoded = atob(value.content_base64);
  if (btoa(decoded) !== value.content_base64)
    throw Error("Original encoding is invalid.");
  const bytes = Uint8Array.from(decoded, (c) => c.charCodeAt(0));
  const actual = Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    (b) => b.toString(16).padStart(2, "0"),
  ).join("");
  if (bytes.length !== value.byte_count || actual !== entry.raw_sha256)
    throw Error("Original failed its exact byte check.");
  // Preserve whitespace and BOM; the server verifies the canonical-source pin.
  return new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(
    bytes,
  );
}
export async function loadInstructorOriginal(
  entry: KeyEntry,
  engagementId: string,
  archive: string,
  signal: AbortSignal,
) {
  const response = await fetch(
    `/api/engagements/${encodeURIComponent(engagementId)}/instructor-key/${encodeURIComponent(entry.id)}/original`,
    {
      credentials: "same-origin",
      cache: "no-store",
      signal,
    },
  );
  if (!response.ok)
    throw Error(
      "Protected original unavailable. Refresh the archive and check your access.",
    );
  if (!response.body) throw Error("Protected original response is empty.");
  const reader = response.body.getReader();
  const parts: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const next = await reader.read();
      if (next.done) break;
      size += next.value.byteLength;
      if (size > RESPONSE_LIMIT)
        throw Error("Protected original exceeds the inspection limit.");
      parts.push(next.value);
    }
  } catch (error) {
    await reader.cancel();
    throw error;
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) {
    bytes.set(part, offset);
    offset += part.length;
  }
  if (signal.aborted)
    throw new DOMException("Inspection cancelled", "AbortError");
  const value = JSON.parse(
    new TextDecoder("utf-8", { fatal: true }).decode(bytes),
  ) as InstructorOriginal;
  return {
    text: await verifyInstructorOriginal(value, entry, engagementId, archive),
    bytes: value.byte_count,
  };
}
export function originalKeyOptions(
  entries: KeyEntry[],
  query: string,
  selected: string,
) {
  const matches = entries.filter((e) =>
    e.id.toLowerCase().includes(query.trim().toLowerCase()),
  );
  const options = matches.slice(0, 50),
    current = entries.find((e) => e.id === selected);
  if (current && !options.some((e) => e.id === selected))
    options.unshift(current);
  return { options, total: matches.length };
}
