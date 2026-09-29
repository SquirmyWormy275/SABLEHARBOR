// Full App task-row focus journey with a long procedures table and isolated GET fixtures.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { chromium } from "@playwright/test";

const port = 8862;
const base = `http://127.0.0.1:${port}`;
const server = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", String(port), "--strictPort"], { stdio: "pipe" });
let browser;
try {
  for (let attempt = 0; attempt < 100; attempt++) {
    try { if ((await fetch(base)).ok) break; } catch {}
    await delay(100);
    if (attempt === 99) throw Error("Vite unavailable");
  }
  browser = await chromium.launch({ headless: true, executablePath: "/usr/bin/chromium" });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [], requests = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const e = {
    id: "E-GAP-FOCUS", title: "Long task table", revision: 1, phase: "ACTIVE",
    discipline: "IT", mode: "CLEAN", simulated_at: "2027-02-01T00:00:00Z",
    permissions: ["learn"],
    scope: { programs: ["SOC2"], boundaries: ["corporate"],
      period_start: "2027-01-01", period_end: "2027-12-31", report_type: "Type 2" },
    company_source_binding: { company: "Sable Harbor", branch: "clean" },
    evidence_acquisition: { mode: "company_source" }, capabilities: {},
    controls: [], people: [],
    tasks: Array.from({ length: 120 }, (_, i) => ({
      id: `T-${String(i + 1).padStart(3, "0")}`, title: `Inspect native source ${i + 1}`,
      status: "NOT_STARTED", conclusion: "NOT_RUN", frameworks: ["SOC2"],
    })),
    task_gaps: [], requests: [], artifacts: [], meetings: [], notes: [],
    populations: [], selections: [], calendar: [], findings: [], workpapers: [],
    reviews: [], surveys: [], events: [], exports: [],
  };
  e.tasks[1].status = "EXCLUDED";
  await page.route("**/api/**", (route) => {
    const req = route.request(), path = new URL(req.url()).pathname;
    requests.push({ method: req.method(), path });
    if (req.method() !== "GET") return route.fulfill({ status: 400, json: { error: "Unexpected mutation" } });
    if (path === "/api/bootstrap") return route.fulfill({ json: {
      viewer: { id: "L", display_name: "Learner", roles: ["learner"] },
      csrf_token: "test", engagements: [{ id: e.id, title: e.title }],
      capabilities: {}, programs: [], people: [], controls: [],
    } });
    if (path === `/api/engagements/${e.id}`) return route.fulfill({ json: structuredClone(e) });
    return route.fulfill({ status: 404, json: { error: "Unexpected API route" } });
  });
  await page.goto(`${base}/?engagement=${e.id}&view=controls`);
  const trigger = page.getByRole("button", { name: "Record gap" }).first();
  await trigger.waitFor();
  await trigger.click();
  const heading = page.getByRole("heading", { name: "Task gap · T-001" });
  await heading.waitFor();
  assert.equal(await heading.evaluate((element) => document.activeElement === element), true,
    "gap panel heading did not receive focus");
  const box = await heading.boundingBox();
  assert(box && box.y >= 0 && box.y < 800, "opened gap panel remained offscreen");
  await page.getByRole("button", { name: "Close gap panel" }).click();
  assert.equal(await trigger.evaluate((element) => document.activeElement === element), true,
    "closing gap did not restore task-row focus");
  assert.equal(await heading.count(), 0);
  const readOnly = page.getByRole("button", { name: "View gaps" }).first();
  await readOnly.click();
  await page.getByRole("heading", { name: "Task gap · T-002" }).waitFor();
  assert.match(await page.getByRole("region", { name: "Task gap record for T-002" }).innerText(), /History remains read-only/);
  await page.getByRole("button", { name: "Close gap panel" }).click();
  assert.equal(await readOnly.evaluate((element) => document.activeElement === element), true);
  assert(requests.every((r) => r.method === "GET"), "focus journey mutated audit state");
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ status: "PASS", task_rows: e.tasks.length, open_focus: true, close_focus: true, excluded_history: true, mutations: 0 }));
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
