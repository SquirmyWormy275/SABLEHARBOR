import { expect, it } from "vitest";
import type { Engagement } from "./api";
import {
  createNavigationMemory,
  orientation,
  parseWorkspaceLink,
  workspaceLink,
} from "./navigation";
const viewer = { id: "user-a", display_name: "Auditor", roles: ["learner"] };
const fixture = () =>
  ({
    id: "eng-a",
    title: "Neutral audit",
    scope: {
      boundaries: ["corporate"],
      programs: ["SOC2"],
      period_start: "2027-01-01",
      period_end: "2027-12-31",
      report_type: "TYPE2",
    },
    permissions: ["read"],
    simulated_at: "2028-01-02T10:00:00Z",
    artifacts: [{ id: "artifact /&1" }],
    tasks: [{ id: "TASK-SH-SEC-003-CHECK:CC7.1" }],
    notes: [],
    workpapers: [],
  }) as unknown as Engagement;
it("round-trips an authorized encoded object ID", () => {
  const location = {
    engagement: "eng-a",
    section: "pbc" as const,
    object: { kind: "artifacts" as const, id: "artifact /&1" },
  };
  expect(parseWorkspaceLink(workspaceLink(location), fixture())).toEqual({
    status: "ready",
    location,
  });
});
it("opens an exact authorized procedure in its control workspace", () => {
  const location = {
    engagement: "eng-a",
    section: "controls" as const,
    object: { kind: "tasks" as const, id: "TASK-SH-SEC-003-CHECK:CC7.1" },
  };
  expect(parseWorkspaceLink(workspaceLink(location), fixture())).toEqual({
    status: "ready",
    location,
  });
  expect(
    parseWorkspaceLink(
      workspaceLink({ ...location, section: "pbc" }),
      fixture(),
    ),
  ).toEqual({ status: "unavailable" });
});
it.each([
  "?engagement=eng-b",
  "?engagement=eng-a&view=private",
  "?engagement=eng-a&view=pbc&kind=private_events&object=x",
  "?engagement=eng-a&view=pbc&kind=artifacts&object=future",
  "?engagement=eng-a&view=notes&kind=artifacts&object=artifact+%2F%261",
  "?engagement=eng-a&engagement=eng-b",
  "?engagement=eng-a&object=x",
  "?kind=notes&object=x",
])("fails closed without revealing object existence: %s", (s) =>
  expect(parseWorkspaceLink(s, fixture())).toEqual({ status: "unavailable" }),
);
it("returns to engagement list and refuses unfetched engagement", () => {
  expect(parseWorkspaceLink("", fixture())).toEqual({ status: "engagements" });
  expect(parseWorkspaceLink("?engagement=eng-a", null)).toEqual({
    status: "unavailable",
  });
});
it("rejects duplicate IDs", () => {
  const e = fixture();
  e.artifacts.push({ ...e.artifacts[0] });
  expect(
    parseWorkspaceLink(
      "?engagement=eng-a&view=pbc&kind=artifacts&object=artifact+%2F%261",
      e,
    ),
  ).toEqual({ status: "unavailable" });
});
it("preserves independent list filters across refresh and returns copies", () => {
  const m = createNavigationMemory(),
    e = fixture();
  m.activate(e, viewer);
  m.save("controls", { query: "access", framework: "SOC2", scrollTop: 160 });
  m.save("pbc", { query: "pending", framework: "all", scrollTop: 20 });
  m.activate({ ...e, revision: 2 }, viewer);
  m.restore("controls").query = "mutated";
  expect(m.restore("controls").query).toBe("access");
  expect(m.restore("pbc").scrollTop).toBe(20);
});
it.each(["source", "acquisition"])(
  "clears list filters on %s context switch while retaining ordinary revision navigation",
  (change) => {
    const m = createNavigationMemory(),
      e = fixture();
    e.company_source_binding = { company: "Sable Harbor", branch: "clean" };
    e.evidence_acquisition = { mode: "company_source" };
    m.activate(e, viewer);
    m.save("controls", { query: "access", framework: "SOC2", scrollTop: 160 });
    m.activate({ ...e, revision: 2 }, viewer);
    expect(m.restore("controls").query).toBe("access");
    const changed = {
      ...e,
      ...(change === "source"
        ? {
            company_source_binding: {
              company: "Sable Harbor",
              branch: "messy",
            },
          }
        : { evidence_acquisition: { mode: "retained_copy" } }),
    };
    m.activate(changed, viewer);
    expect(m.restore("controls")).toEqual({
      query: "",
      framework: "all",
      scrollTop: 0,
    });
  },
);
it.each(["engagement", "scope", "permissions", "viewer", "roles", "logout"])(
  "discards filters on %s change",
  (change) => {
    const m = createNavigationMemory(),
      e = fixture(),
      v = { ...viewer };
    m.activate(e, v);
    m.save("controls", {
      query: "private search",
      framework: "SOC2",
      scrollTop: 20,
    });
    if (change === "engagement") e.id = "eng-b";
    if (change === "scope") e.scope.boundaries = ["other"];
    if (change === "permissions") e.permissions = [];
    if (change === "viewer") v.id = "user-b";
    if (change === "roles") v.roles = ["company"];
    if (change === "logout") m.clear();
    else m.activate(e, v);
    expect(m.restore("controls")).toEqual({
      query: "",
      framework: "all",
      scrollTop: 0,
    });
  },
);
it("does not cache before authorization and normalizes invalid positions", () => {
  const m = createNavigationMemory();
  m.save("notes", { query: "x", framework: "all", scrollTop: NaN });
  expect(m.restore("notes").query).toBe("");
  m.activate(fixture(), viewer);
  m.save("notes", { query: "x", framework: "all", scrollTop: Infinity });
  expect(m.restore("notes").scrollTop).toBe(0);
});
it("uses actual scope orientation without mutating arrays", () => {
  const e = fixture(),
    o = orientation(e, viewer);
  o.boundaries.push("other");
  expect(e.scope.boundaries).toEqual(["corporate"]);
  expect(o.periodEnd).toBe("2027-12-31");
});
