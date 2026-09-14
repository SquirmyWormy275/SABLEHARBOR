import { expect, it } from "vitest";
import {
  createDraftStore,
  type DraftKey,
  type DraftScope,
} from "./draftContext";
const scope = (): DraftScope => ({
  actorId: "actor-a",
  engagementId: "eng-a",
  roles: ["learner"],
  permissions: ["learn"],
  scope: { period: "2027", boundary: "corporate" },
});
const key = (): DraftKey => ({
  actorId: "actor-a",
  engagementId: "eng-a",
  kind: "workpaper.update",
  objectId: "WP-1",
  baseVersion: "1",
});
const setup = () => {
  const s = createDraftStore();
  s.activate(scope());
  return s;
};
it("preserves current editable values and returns defensive copies", () => {
  const s = setup();
  s.save(key(), {
    objective: "Inspect original",
    text: "Unsent text",
    hidden_rubric: "DO NOT RETAIN",
    workpaper_id: "other",
  });
  const found = s.lookup(key());
  expect(found.status).toBe("CURRENT");
  if (found.status === "EMPTY") throw Error();
  expect(found.draft.values).toEqual({
    objective: "Inspect original",
    text: "Unsent text",
  });
  found.draft.values.text = "changed";
  expect(s.lookup(key())).not.toEqual(found);
  s.activate(scope());
  expect(s.lookup(key()).status).toBe("CURRENT");
});
it("marks stale base without silently moving it; explicit rebase preserves prior version", () => {
  const s = setup();
  s.save(key(), { text: "v1 draft" });
  const next = { ...key(), baseVersion: "2" };
  const old = s.lookup(next);
  expect(old.status).toBe("STALE_BASE");
  if (old.status === "EMPTY") throw Error();
  expect(old.draft.key.baseVersion).toBe("1");
  s.rebase(old.draft.key, next);
  expect(s.lookup(next).status).toBe("CURRENT");
  expect(s.lookup(key()).status).toBe("CURRENT");
});
it.each(["actor", "engagement", "scope", "permissions", "roles"])(
  "clears all retained text on %s switch",
  (field) => {
    const s = setup();
    s.save(key(), { text: "private draft" });
    const changed = scope();
    if (field === "actor") changed.actorId = "actor-b";
    if (field === "engagement") changed.engagementId = "eng-b";
    if (field === "scope") changed.scope = { period: "2028" };
    if (field === "permissions") changed.permissions = ["instruct"];
    if (field === "roles") changed.roles = ["instructor"];
    s.activate(changed);
    const target = {
      ...key(),
      actorId: changed.actorId,
      engagementId: changed.engagementId,
    };
    expect(s.lookup(target).status).toBe("EMPTY");
  },
);
it("clears authorization on logout and rejects cross-object rebase", () => {
  const s = setup();
  s.save(key(), { text: "draft" });
  expect(() => s.rebase(key(), { ...key(), objectId: "WP-2" })).toThrow();
  s.clear();
  expect(() => s.lookup(key())).toThrow("authorized");
  s.activate(scope());
  expect(s.lookup(key()).status).toBe("EMPTY");
});
it("discard removes only requested object drafts and does not submit", () => {
  const s = setup();
  s.save(key(), { text: "one" });
  s.save({ ...key(), objectId: "WP-2" }, { text: "two" });
  s.rebase(key(), { ...key(), baseVersion: "2" });
  s.discardObject(key());
  expect(s.lookup(key()).status).toBe("EMPTY");
  expect(s.lookup({ ...key(), objectId: "WP-2" }).status).toBe("CURRENT");
});
it("supports new notes with a stable NEW base and no arbitrary nested records", () => {
  const s = setup(),
    note = {
      ...key(),
      kind: "note.create" as const,
      objectId: "new",
      baseVersion: "NEW",
    };
  s.save(note, { title: "Unsent note", text: "Observation" });
  expect(s.lookup(note).status).toBe("CURRENT");
  expect(() => s.save(note, { text: { private: "nested" } })).toThrow(
    "plain form",
  );
});
it("does not silently evict drafts or replace them on oversize failure", () => {
  const s = setup();
  s.save(key(), { text: "keep" });
  expect(() => s.save(key(), { text: "x".repeat(100001) })).toThrow(
    "size limit",
  );
  const found = s.lookup(key());
  expect(found.status !== "EMPTY" && found.draft.values.text).toBe("keep");
  for (let i = 1; i < 32; i++)
    s.save({ ...key(), objectId: `WP-${i + 1}` }, { text: "keep" });
  expect(() =>
    s.save({ ...key(), objectId: "EXTRA" }, { text: "new" }),
  ).toThrow("limit");
  expect(s.lookup(key()).status).toBe("CURRENT");
});
it("rejects retention when fetched permissions do not permit writing", () => {
  const s = setup();
  s.activate({ ...scope(), permissions: ["review"] });
  expect(() => s.save(key(), { text: "no" })).toThrow("authorized");
});

it("retains new workpaper section/code metadata without arbitrary objects", () => {
  const s = setup(),
    draft = {
      ...key(),
      kind: "workpaper.add" as const,
      objectId: "new",
      baseVersion: "NEW",
    };
  s.save(draft, {
    title: "Neutral paper",
    section: "testing",
    code: "TEST-1",
    text: "Draft",
    private_graph: { secret: true },
  });
  const found = s.lookup(draft);
  expect(found.status !== "EMPTY" && found.draft.values).toEqual({
    title: "Neutral paper",
    section: "testing",
    code: "TEST-1",
    text: "Draft",
  });
});
