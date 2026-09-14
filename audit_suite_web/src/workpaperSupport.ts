import { artifactURL, type Engagement, type Row } from "./api";

export const PREVIEW_LIMIT = 1024 * 1024;
export function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}
export function availableArtifact(
  engagement: Engagement,
  id: string,
): Row | undefined {
  return engagement.artifacts.find(
    (row) => row.id === id && row.status === "AVAILABLE",
  );
}
export function previewKey(
  viewer: string,
  engagement: Engagement,
  artifact: Row,
): string {
  return JSON.stringify([
    viewer,
    engagement.id,
    engagement.revision,
    engagement.permissions,
    engagement.simulated_at,
    artifact.id,
    artifact.sha256,
    artifact.status,
  ]);
}
export function acceptsPreview(
  expected: string,
  viewer: string,
  engagement: Engagement,
  id: string,
): boolean {
  const artifact = availableArtifact(engagement, id);
  return !!artifact && previewKey(viewer, engagement, artifact) === expected;
}
export function textPreviewAllowed(artifact: Row): boolean {
  return ["text/plain", "text/csv", "application/json"].includes(
    String(artifact.mime),
  );
}
export function supportingTasks(
  engagement: Engagement,
  controlId: string,
): Row[] {
  if (!engagement.controls.some((control) => control.id === controlId))
    return [];
  return engagement.tasks.filter((task) => task.control_id === controlId);
}
export function evidenceReference(artifact: Row): string {
  const source = record(record(record(artifact.source).receipt).source);
  return `${artifact.id}; SHA-256 ${String(artifact.sha256)}${source.record ? `; source ${String(source.system)}/${String(source.record)} v${String(source.version)}` : ""}`;
}
export async function loadTextPreview(
  engagementId: string,
  artifact: Row,
  signal: AbortSignal,
): Promise<string> {
  if (!textPreviewAllowed(artifact) || artifact.status !== "AVAILABLE")
    throw new Error("Inline text preview unavailable for this original.");
  if (typeof artifact.bytes !== "number" || artifact.bytes > PREVIEW_LIMIT)
    throw new Error(
      "Original exceeds the 1 MiB inline preview limit. Download it for inspection.",
    );
  const response = await fetch(artifactURL(engagementId, artifact.id), {
    credentials: "same-origin",
    signal,
  });
  if (!response.ok)
    throw new Error(`Original unavailable (${response.status}).`);
  if (!response.body) throw new Error("Original response is unreadable.");
  const reader = response.body.getReader();
  const parts: Uint8Array[] = [];
  let count = 0;
  try {
    while (true) {
      const item = await reader.read();
      if (item.done) break;
      count += item.value.byteLength;
      if (count > PREVIEW_LIMIT)
        throw new Error("Original exceeds the inline preview limit.");
      parts.push(item.value);
    }
  } catch (error) {
    await reader.cancel();
    throw error;
  } finally {
    reader.releaseLock();
  }
  if (signal.aborted) throw new DOMException("Preview cancelled", "AbortError");
  const bytes = new Uint8Array(count);
  let offset = 0;
  for (const part of parts) {
    bytes.set(part, offset);
    offset += part.length;
  }
  const actual = Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    (byte) => byte.toString(16).padStart(2, "0"),
  ).join("");
  if (actual !== artifact.sha256 || count !== artifact.bytes)
    throw new Error("Original changed or failed its retained hash check.");
  return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
}

/** Normalize a form's explicit IDs only; never infer relevance or promote evidence. */
export function appendEvidenceReference(
  current: unknown,
  artifactId: string,
): string[] {
  const values = Array.isArray(current)
    ? current.filter((id): id is string => typeof id === "string")
    : typeof current === "string"
      ? current.split(/[\s,;]+/)
      : [];
  return [
    ...new Set([...values.map((id) => id.trim()).filter(Boolean), artifactId]),
  ];
}
