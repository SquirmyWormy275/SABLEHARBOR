import type { Capabilities } from "./api";

/** Missing capability means an older server; never probe optional mutation routes. */
export function supports(caps: Capabilities, name: string): boolean {
  return caps[name] === true;
}

export function compatibleWorkpaperValues(
  kind: string,
  values: Record<string, unknown>,
  caps: Capabilities,
): Record<string, unknown> {
  if (
    !["workpaper.add", "workpaper.update"].includes(kind) ||
    supports(caps, "workpaper_procedure_links")
  )
    return values;
  const result = { ...values };
  delete result.task_ids;
  return result;
}
