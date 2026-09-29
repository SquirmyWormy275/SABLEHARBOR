// Compiled-App context switch regression. All API responses are isolated fixtures.
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";

const base = "http://127.0.0.1:8851";
const server = spawn(
  process.execPath,
  ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "8851", "--strictPort"],
  { stdio: "pipe" },
);
let browser;
try {
  for (let attempt = 0; attempt < 100; attempt++) {
    try {
      if ((await fetch(base)).ok) break;
    } catch {}
    await delay(100);
    if (attempt === 99) throw Error("Vite unavailable");
  }
  browser = await chromium.launch({ headless: true, executablePath: "/usr/bin/chromium" });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [], requests = [], actions = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const engagement = {
    id: "E-CONTEXT", title: "Context switch fixture", revision: 1,
    phase: "ACTIVE", discipline: "IT", mode: "CLEAN",
    simulated_at: "2027-01-01T00:00:00Z", permissions: ["learn"],
    scope: { programs: ["SOC2"], boundaries: ["corporate"],
      period_start: "2027-01-01", period_end: "2027-12-31", report_type: "Type 2" },
    company_source_binding: { company: "Sable Harbor", branch: "clean" },
    evidence_acquisition: { mode: "company_source" },
    capabilities: {},
    controls: [{ id: "C1", title: "Old access review", frameworks: ["SOC2"] }],
    people: [], tasks: [], requests: [], artifacts: [], meetings: [], notes: [],
    populations: [], selections: [], calendar: [], findings: [], workpapers: [],
    reviews: [], surveys: [], events: [], exports: [],
  };
  await page.route("**/api/**", (route) => {
    const req = route.request(), path = new URL(req.url()).pathname;
    requests.push({ method: req.method(), path });
    if (req.method() !== "GET")
      return route.fulfill({ status: 400, json: { error: "Unexpected mutation" } });
    if (path === "/api/bootstrap")
      return route.fulfill({ json: {
        viewer: { id: "L", display_name: "Learner", roles: ["learner"] },
        csrf_token: "test", engagements: [{ id: engagement.id, title: engagement.title }],
        capabilities: {}, programs: [], people: [], controls: [],
      } });
    if (path === `/api/engagements/${engagement.id}`)
      return route.fulfill({ json: structuredClone(engagement) });
    return route.fulfill({ status: 404, json: { error: "Unexpected API route" } });
  });
  async function act(name, work) { actions.push(name); await work(); }
  async function refresh() {
    await act("refresh current engagement", () =>
      page.evaluate(() => dispatchEvent(new PopStateEvent("popstate"))));
    await page.getByText(`revision ${engagement.revision}`, { exact: false }).waitFor();
  }
  await act("open controls deep link", () => page.goto(`${base}/?engagement=${engagement.id}&view=controls`));
  await page.getByRole("heading", { name: "Common control register" }).waitFor();
  const search = page.getByRole("searchbox", { name: "Search this engagement" });
  const controls = page.getByRole("heading", { name: "Common control register" })
    .locator("xpath=following-sibling::div[1]");
  const tableSearch = controls.getByRole("searchbox", { name: "Search records" });
  await act("open global search", () => page.keyboard.press("Control+k"));
  await act("search old support", () => search.fill("Old"));
  await act("submit global search", () =>
    page.getByRole("button", { name: "Search records", exact: true }).click());
  await act("filter control table", () => tableSearch.fill("Old"));
  await page.getByRole("button", { name: "Preview C1", exact: true }).waitFor();
  assert.equal(await tableSearch.inputValue(), "Old");

  engagement.revision++;
  await refresh();
  assert.equal(await search.inputValue(), "Old", "ordinary revision should retain submitted query");
  assert.equal(await tableSearch.inputValue(), "Old", "ordinary revision should retain table position");

  engagement.company_source_binding = { company: "Sable Harbor", branch: "messy" };
  engagement.controls = [{ id: "C1", title: "Corrected access review", frameworks: ["SOC2"] }];
  engagement.revision++;
  await refresh();
  await act("reopen search after source switch", () => page.keyboard.press("Control+k"));
  assert.equal(await search.inputValue(), "", "source switch retained prior query");
  assert.equal(await tableSearch.inputValue(), "", "source switch retained prior table filter");
  await controls.getByRole("button", { name: "C1", exact: true }).waitFor();

  await act("search corrected support", () => search.fill("Corrected"));
  await act("submit corrected search", () =>
    page.getByRole("button", { name: "Search records", exact: true }).click());
  await act("filter corrected table", () => tableSearch.fill("Corrected"));
  engagement.evidence_acquisition = { mode: "retained_copy" };
  engagement.controls = [{ id: "C1", title: "Retained access review", frameworks: ["SOC2"] }];
  engagement.revision++;
  await refresh();
  await act("reopen search after acquisition switch", () => page.keyboard.press("Control+k"));
  assert.equal(await search.inputValue(), "", "acquisition switch retained prior query");
  assert.equal(await tableSearch.inputValue(), "", "acquisition switch retained prior table filter");
  await controls.getByRole("button", { name: "C1", exact: true }).waitFor();
  assert.deepEqual(errors, []);
  assert.ok(requests.every((r) => r.method === "GET"), "journey issued mutation");
  assert.ok(requests.every((r) =>
    ["/api/bootstrap", `/api/engagements/${engagement.id}`].includes(r.path)),
  "journey requested unexpected route");
  console.log(JSON.stringify({ status: "PASS", actions: actions.length,
    requests: requests.length, stages: ["ordinary revision retention", "source switch reset", "acquisition switch reset"],
    mutations: 0, page_errors: errors.length }));
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
