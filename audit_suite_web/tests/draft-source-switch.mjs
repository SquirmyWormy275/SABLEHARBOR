// Read-only fixture journey: source changes retain authored text, never old links.
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";

const base = "http://127.0.0.1:8852";
const server = spawn(process.execPath,
  ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "8852", "--strictPort"],
  { stdio: "pipe" });
let browser;
try {
  for (let i = 0; i < 100; i++) {
    try { if ((await fetch(base)).ok) break; } catch {}
    await delay(100);
    if (i === 99) throw Error("Vite unavailable");
  }
  browser = await chromium.launch({ headless: true, executablePath: "/usr/bin/chromium" });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const pageErrors = [], requests = [], actions = [], commands = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  const e = {
    id: "E-DRAFT", title: "Draft source switch fixture", revision: 1,
    phase: "ACTIVE", discipline: "IT", mode: "CLEAN",
    simulated_at: "2027-01-01T00:00:00Z", permissions: ["learn"],
    scope: { programs: ["SOC2"], boundaries: ["corporate"],
      period_start: "2027-01-01", period_end: "2027-12-31", report_type: "Type 2" },
    company_source_binding: { company: "Sable Harbor", branch: "clean" },
    evidence_acquisition: "COMPANY_SOURCE_COLLECTION",
    capabilities: { personal_drafts: true },
    controls: [{ id: "C1", title: "Access review", frameworks: ["SOC2"] }],
    tasks: [{ id: "T1", title: "Inspect approval", control_id: "C1",
      status: "NOT_STARTED", conclusion: "NOT_RUN" }],
    artifacts: [{ id: "OLD-A", title: "Old original", status: "AVAILABLE" },
      { id: "NEW-A", title: "New original", status: "AVAILABLE" }],
    people: [], requests: [], meetings: [], notes: [], populations: [],
    selections: [], calendar: [], findings: [],
    workpapers: [{ id: "W1", title: "Historical workpaper", control_id: "C1",
      versions: [{ version: 1, objective: "Old objective", procedures: "Old procedure",
        evidence_ids: ["OLD-A"], conclusion: "OPEN", text: "Earlier text" }] }],
    reviews: [],
    surveys: [], events: [], exports: [],
  };
  const basis = () => JSON.stringify([e.company_source_binding, e.evidence_acquisition]);
  let saved = { status: "EMPTY", version: 0, fields: {}, base_workpaper_version: null, context: basis() };
  const otherDrafts = new Map();
  await page.route("**/api/**", (route) => {
    const req = route.request(), path = new URL(req.url()).pathname, method = req.method();
    requests.push({ method, path });
    if (path === "/api/bootstrap" && method === "GET")
      return route.fulfill({ json: { viewer: { id: "L", display_name: "Learner", roles: ["learner"] },
        csrf_token: "test", engagements: [{ id: e.id, title: e.title }],
        capabilities: e.capabilities, programs: [], people: [], controls: [] } });
    if (path === `/api/engagements/${e.id}` && method === "GET")
      return route.fulfill({ json: structuredClone(e) });
    if (path.includes("/drafts/")) {
      const isNew = path.endsWith("/new");
      let draftRow = isNew ? saved : (otherDrafts.get(path) ?? {
        status: "EMPTY", version: 0, fields: {}, base_workpaper_version: null, context: basis(),
      });
      const payload = method === "GET" ? null : req.postDataJSON();
      if (method === "PUT" && (draftRow.status === "STALE_SOURCE" ||
          (draftRow.status === "DRAFT" && draftRow.context !== basis())))
        return route.fulfill({ status: 409, json: { error: "Stale draft requires explicit discard" } });
      if (payload && payload.expected_version !== draftRow.version)
        return route.fulfill({ status: 409, json: { error: "Draft version changed" } });
      if (method === "PUT") draftRow = { status: "DRAFT", version: draftRow.version + 1,
        fields: payload.fields, base_workpaper_version: payload.base_workpaper_version, context: basis() };
      if (method === "DELETE") draftRow = { status: "EMPTY", version: draftRow.version + 1,
        fields: {}, base_workpaper_version: null, context: basis() };
      if (isNew) saved = draftRow; else otherDrafts.set(path, draftRow);
      const visible = draftRow.status === "DRAFT" && draftRow.context !== basis()
        ? { status: "STALE", version: draftRow.version, base_workpaper_version: draftRow.base_workpaper_version }
        : { ...draftRow, context: undefined };
      return route.fulfill({ json: { ...visible, workpaper_stale: false } });
    }
    if (path === `/api/engagements/${e.id}/commands` && method === "POST") {
      const command = req.postDataJSON();
      commands.push(command);
      e.revision++;
      return route.fulfill({ json: structuredClone(e) });
    }
    return route.fulfill({ status: 404, json: { error: "Unexpected API route" } });
  });
  async function act(label, callback) { actions.push(label); await callback(); }
  async function refresh() {
    await act("refresh same engagement", () =>
      page.evaluate(() => dispatchEvent(new PopStateEvent("popstate"))));
    await page.getByText(`revision ${e.revision}`, { exact: false }).waitFor();
  }
  await act("open review", () => page.goto(`${base}/?engagement=${e.id}&view=review`));
  await page.getByRole("button", { name: "New structured workpaper", exact: true }).waitFor();
  await act("start workpaper", () =>
    page.getByRole("button", { name: "New structured workpaper", exact: true }).click());
  let form = page.getByRole("dialog");
  await act("author title", () => form.getByLabel("Workpaper title", { exact: true }).fill("Authored analysis"));
  await act("choose control", () => form.getByLabel("Control", { exact: true }).selectOption("C1"));
  await act("choose section", () => form.getByLabel("Section", { exact: true }).selectOption("testing"));
  await act("author objective", () => form.getByLabel("Objective", { exact: true }).fill("Inspect current support"));
  await act("author procedure", () => form.getByLabel("Nature, timing and extent", { exact: true }).fill("Compare approval"));
  await act("link old original", () => form.getByLabel("Evidence references", { exact: true }).fill("OLD-A"));
  await act("author limitation", () => form.getByLabel("Conclusion and limitations", { exact: true }).fill("Open pending support"));
  for (let i = 0; i < 100 && saved.status !== "DRAFT"; i++) await delay(50);
  assert.equal(saved.status, "DRAFT", "draft was not saved before source switch");
  const savedVersion = saved.version;

  e.company_source_binding = { company: "Sable Harbor", branch: "messy" };
  e.revision++;
  await refresh();
  form = page.getByRole("dialog");
  await form.getByText("Source context changed.", { exact: true }).waitFor();
  assert.equal(await form.getByLabel("Workpaper title", { exact: true }).inputValue(), "Authored analysis");
  assert.equal(await form.getByLabel("Evidence references", { exact: true }).inputValue(), "OLD-A");
  assert.equal(await form.getByLabel("Evidence references", { exact: true }).isDisabled(), true);
  assert.equal(await form.getByRole("button", { name: "Save record", exact: true }).isDisabled(), true);
  assert.equal(saved.version, savedVersion, "source switch silently rewrote persisted draft");
  assert.deepEqual(commands, [], "source switch submitted formal command");
  await act("carry text without old links", () => form.getByRole("button", {
    name: "Keep my text; clear old links and discard stale saved copy", exact: true,
  }).click());
  await page.waitForFunction(() =>
    document.querySelector('input[aria-label="Evidence references"]')?.value === "");
  assert.equal(await form.getByLabel("Workpaper title", { exact: true }).inputValue(), "Authored analysis");
  assert.equal(await form.getByLabel("Evidence references", { exact: true }).inputValue(), "");
  assert.equal(await form.getByLabel("Control", { exact: true }).inputValue(), "");
  assert.equal(await form.getByLabel("Evidence references", { exact: true }).isEnabled(), true);
  await act("reselect current control", () => form.getByLabel("Control", { exact: true }).selectOption("C1"));
  await act("reselect current original", () => form.getByLabel("Evidence references", { exact: true }).fill("NEW-A"));
  await act("submit reviewed workpaper", () => form.getByRole("button", { name: "Save record", exact: true }).click());
  await form.waitFor({ state: "hidden" });
  assert.equal(commands.length, 1);
  assert.equal(commands[0].kind, "workpaper.add");
  assert.equal(commands[0].payload.evidence_ids, "NEW-A");
  assert.ok(!JSON.stringify(commands[0]).includes("OLD-A"));

  await act("open earlier workpaper", () => page.goto(`${base}/?engagement=${e.id}&view=review`));
  await page.getByRole("button", { name: "New structured workpaper", exact: true }).waitFor();
  await act("open record search", () => page.keyboard.press("Control+k"));
  await act("find earlier workpaper", () =>
    page.getByRole("searchbox", { name: "Search this engagement" }).fill("W1"));
  await act("submit workpaper search", () =>
    page.getByRole("button", { name: "Search records", exact: true }).click());
  await act("preview earlier workpaper", () =>
    page.getByRole("button", { name: "Preview W1", exact: true }).click());
  await act("open untouched successor form", () =>
    page.getByRole("button", { name: "Save new version", exact: true }).click());
  form = page.getByRole("dialog");
  assert.equal(await form.getByLabel("Evidence references", { exact: true }).inputValue(), "OLD-A");
  e.evidence_acquisition = "RETAINED_COPY";
  e.revision++;
  await refresh();
  form = page.getByRole("dialog");
  await form.getByText("Source context changed.", { exact: true }).waitFor();
  assert.equal(await form.getByLabel("Evidence references", { exact: true }).isDisabled(), true);
  assert.equal(await form.getByRole("button", { name: "Save record", exact: true }).isDisabled(), true);
  assert.equal(commands.length, 1, "untouched old-linked form submitted");
  await act("close untouched stale draft", () =>
    form.getByRole("button", { name: "Close (keep draft)", exact: true }).click());

  await act("open controls", () => page.goto(`${base}/?engagement=${e.id}&view=controls`));
  await page.getByRole("button", { name: "T1", exact: true }).click();
  form = page.getByRole("dialog");
  e.evidence_acquisition = "OTHER_ACQUISITION";
  e.revision++;
  await refresh();
  form = page.getByRole("dialog");
  await form.getByText("Close it and reopen the current record before submitting.", { exact: false }).waitFor();
  assert.equal(await form.getByRole("button", { name: "Save record", exact: true }).isDisabled(), true);
  assert.equal(await form.getByRole("button", { name: /Keep my text; clear old links/ }).count(), 0);
  await act("close stale non-draft action", () => form.getByRole("button", { name: "Cancel", exact: true }).click());
  assert.equal(commands.length, 1, "non-draft stale action submitted");

  // Simulate the service's narrative-only projection of an exact-match legacy
  // digest. Its old source links are absent, and the old row remains intact
  // until the user explicitly chooses discard and carry-forward.
  saved = { status: "STALE_SOURCE", version: 9,
    fields: { title: "Legacy authored narrative", objective: "Inspect legacy scope" },
    base_workpaper_version: null, context: basis() };
  await act("open legacy narrative", () => page.goto(`${base}/?engagement=${e.id}&view=review`));
  await page.getByRole("button", { name: "New structured workpaper", exact: true }).waitFor();
  await act("start legacy successor", () =>
    page.getByRole("button", { name: "New structured workpaper", exact: true }).click());
  form = page.getByRole("dialog");
  await form.getByText("Source context changed.", { exact: true }).waitFor();
  assert.equal(await form.getByLabel("Workpaper title", { exact: true }).inputValue(), "Legacy authored narrative");
  assert.equal(await form.getByLabel("Objective", { exact: true }).inputValue(), "Inspect legacy scope");
  assert.equal(await form.getByLabel("Evidence references", { exact: true }).inputValue(), "");
  assert.equal(await form.getByRole("button", { name: "Save record", exact: true }).isDisabled(), true);
  assert.equal(saved.version, 9, "legacy row changed before explicit discard");
  await act("carry recovered legacy text", () => form.getByRole("button", {
    name: "Keep my text; clear old links and discard stale saved copy", exact: true,
  }).click());
  await page.waitForFunction(() =>
    document.querySelector('input[aria-label="Evidence references"]')?.disabled === false);
  assert.equal(await form.getByLabel("Workpaper title", { exact: true }).inputValue(), "Legacy authored narrative");
  assert.equal(await form.getByLabel("Evidence references", { exact: true }).inputValue(), "");
  assert.equal(await form.getByLabel("Evidence references", { exact: true }).isEnabled(), true);
  await act("reselect legacy successor control", () => form.getByLabel("Control", { exact: true }).selectOption("C1"));
  await act("select legacy successor section", () => form.getByLabel("Section", { exact: true }).selectOption("testing"));
  await act("author legacy successor procedure", () => form.getByLabel("Nature, timing and extent", { exact: true }).fill("Inspect current originals"));
  await act("select legacy successor original", () => form.getByLabel("Evidence references", { exact: true }).fill("NEW-A"));
  await act("author legacy successor limitation", () => form.getByLabel("Conclusion and limitations", { exact: true }).fill("Open pending review"));
  await act("submit legacy successor", () => form.getByRole("button", { name: "Save record", exact: true }).click());
  await form.waitFor({ state: "hidden" });
  assert.equal(commands.length, 2);
  assert.equal(commands[1].payload.evidence_ids, "NEW-A");
  assert.ok(!JSON.stringify(commands[1]).includes("OLD-A"));
  assert.deepEqual(pageErrors, []);
  console.log(JSON.stringify({ status: "PASS", actions: actions.length,
    requests: requests.length, formal_fixture_commands: commands.length,
    stale_draft_writes: 0, page_errors: pageErrors.length,
    stages: ["saved stale draft withheld", "volatile text retained and old links cleared", "new link selected before formal fixture submission", "untouched old-linked form denied", "non-draft stale action denied", "legacy narrative recovered without links"] }));
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
