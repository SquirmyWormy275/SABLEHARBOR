import { beforeEach, expect, it, vi } from "vitest";
import { ApiError, request } from "./api";
import {
  deleteDraft,
  draftFields,
  draftURL,
  formDraftFields,
  readDraft,
  writeDraft,
  draftConflict,
} from "./durableDraft";
import type { DraftKey } from "./draftContext";
vi.mock("./api", async (original) => ({
  ...(await original<typeof import("./api")>()),
  request: vi.fn(),
}));
const key: DraftKey = {
  actorId: "a",
  engagementId: "ENG /1",
  kind: "workpaper.update",
  objectId: "WP /2",
  baseVersion: "3",
};
beforeEach(() => vi.mocked(request).mockReset());
it("encodes scoped endpoint without actor identity or body text in URL", () => {
  expect(draftURL(key)).toBe(
    "/api/engagements/ENG%20%2F1/drafts/workpaper.update/WP%20%2F2",
  );
});
it("transports explicit optimistic revision, stable command ID and exactworkpaperbase", async () => {
  vi.mocked(request).mockResolvedValue({ status: "DRAFT", version: 8 });
  await writeDraft(
    key,
    7,
    { text: "Draft", evidence_ids: "A1, A2", private_key: "NEVER" },
    "stable-command",
  );
  expect(request).toHaveBeenCalledWith(draftURL(key), "PUT", {
    command_id: "stable-command",
    expected_version: 7,
    fields: { text: "Draft", evidence_ids: ["A1", "A2"] },
    base_workpaper_version: 3,
  });
});
it("does not retry409 silently and supports delete using tombstone version", async () => {
  vi.mocked(request).mockRejectedValueOnce(new ApiError("Concurrent", 409));
  await expect(writeDraft(key, 7, { text: "Draft" }, "one")).rejects.toThrow(
    "Concurrent",
  );
  expect(request).toHaveBeenCalledTimes(1);
  expect(draftConflict(new ApiError("Concurrent", 409))).toBe(true);
  vi.mocked(request).mockResolvedValue({ status: "EMPTY", version: 9 });
  await deleteDraft(key, 8, "delete");
  expect(request).toHaveBeenLastCalledWith(draftURL(key), "DELETE", {
    command_id: "delete",
    expected_version: 8,
  });
});
it("keeps allowed note routing fields and converts evidence references without arbitrary metadata", () => {
  const note = {
    ...key,
    kind: "note.create" as const,
    objectId: "new",
    baseVersion: "NEW",
  };
  expect(
    draftFields(note, {
      title: "n",
      text: "t",
      control_id: "C1",
      source_message_id: "M1",
      rubric: { hidden: "x" },
    }),
  ).toEqual({
    title: "n",
    text: "t",
    control_id: "C1",
    source_message_id: "M1",
  });
  expect(formDraftFields({ evidence_ids: ["A1", "A2"], text: "t" })).toEqual({
    evidence_ids: "A1, A2",
    text: "t",
  });
});
it("reads only the selected personal scoped draft", async () => {
  vi.mocked(request).mockResolvedValue({ status: "EMPTY", version: 4 });
  await readDraft(key);
  expect(request).toHaveBeenCalledWith(draftURL(key));
});

it("keeps explicit procedure arrays and scoped control across creation draft recovery", () => {
  const creation = { ...key, kind: "workpaper.add" as const };
  expect(
    draftFields(creation, {
      control_id: "C1",
      task_ids: ["T1"],
      title: "Paper",
    }),
  ).toEqual({ title: "Paper", task_ids: ["T1"], control_id: "C1" });
  expect(formDraftFields({ task_ids: ["T1"] }).task_ids).toEqual(["T1"]);
});
