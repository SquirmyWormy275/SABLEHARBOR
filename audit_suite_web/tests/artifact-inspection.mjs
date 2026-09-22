// Compiled application, neutral projections only; no actual audit or model calls.
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
const output = resolve(
  "../enterprise/generated/audit-suite/build/artifact-inspection",
);
await mkdir(output, { recursive: true });
const server = spawn(
  process.execPath,
  [
    "node_modules/vite/bin/vite.js",
    "preview",
    "--host",
    "127.0.0.1",
    "--port",
    "5201",
    "--strictPort",
  ],
  { stdio: "ignore" },
);
let browser;
try {
  for (let i = 0; i < 50; i++) {
    try {
      if ((await fetch("http://127.0.0.1:5201")).ok) break;
    } catch {}
    await new Promise((r) => setTimeout(r, 100));
  }
  browser = await chromium.launch({
    executablePath: "/usr/bin/chromium",
    headless: true,
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({
    viewport: { width: 1360, height: 1000 },
  });
  page.setDefaultTimeout(8000);
  const errors = [],
    commands = [],
    unexpected = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const e = {
    id: "ENG-INSPECTION",
    title: "Neutral exact-original inspection",
    revision: 4,
    discipline: "IT",
    mode: "MESSY",
    phase: "ACTIVE",
    simulated_at: "2027-02-12T09:00:00Z",
    scope: {
      programs: ["SOC2"],
      period_start: "2027-01-01",
      period_end: "2027-12-31",
      report_type: "Type 2",
      boundaries: ["corporate"],
    },
    permissions: ["learn"],
    capabilities: { artifact_inspections: true },
    controls: [{ id: "C-1", title: "Neutral access procedure" }],
    tasks: [
      {
        id: "T-1",
        title: "Inspect approval",
        control_id: "C-1",
        status: "NOT_STARTED",
        conclusion: "NOT_RUN",
      },
    ],
    artifacts: [
      {
        id: "ART-1",
        name: "review.csv",
        status: "AVAILABLE",
        sha256: "a".repeat(64),
        version: 2,
        bytes: 10,
        mime: "text/csv",
      },
    ],
    people: [],
    requests: [],
    meetings: [],
    notes: [],
    populations: [],
    selections: [],
    calendar: [],
    findings: [],
    workpapers: [],
    reviews: [],
    surveys: [],
    events: [],
    artifact_inspections: [],
  };
  let reject = true;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname,
      method = route.request().method();
    if (path === "/api/bootstrap")
      return route.fulfill({
        json: {
          viewer: {
            id: "USER-1",
            display_name: "Neutral learner",
            roles: ["learner"],
          },
          csrf_token: "fixture",
          engagements: [e],
          capabilities: e.capabilities,
          programs: [],
          people: [],
          controls: [],
        },
      });
    if (path === `/api/engagements/${e.id}` && method === "GET")
      return route.fulfill({ json: e });
    if (path === `/api/engagements/${e.id}/commands` && method === "POST") {
      const v = route.request().postDataJSON();
      commands.push(v);
      assert.equal(v.kind, "artifact.inspection.record");
      assert.equal(v.expected_revision, 4);
      assert.deepEqual(v.payload, {
        artifact_id: "ART-1",
        sha256: "a".repeat(64),
        version: 2,
        locator: "Rows 1–3",
        observation:
          "Approval is absent in the retained rows.\nFurther inquiry is needed.",
      });
      if (reject)
        return route.fulfill({
          status: 422,
          json: { error: "Original integrity check failed" },
        });
      e.revision++;
      e.artifact_inspections.push({
        ...v.payload,
        id: "INSPECT-1",
        classification: "SELF_REPORTED_INSPECTION",
        actor: "USER-1",
        recorded_at: "2026-09-22T17:00:00Z",
        simulated_at: e.simulated_at,
        recorded_revision: 5,
        task_id: null,
      });
      return route.fulfill({ json: e });
    }
    unexpected.push(`${method} ${path}`);
    return route.fulfill({
      status: 404,
      json: { error: "Unexpected fixture request" },
    });
  });
  await page.goto(`http://127.0.0.1:5201/?engagement=${e.id}&view=pbc`);
  await page.getByText("review.csv", { exact: true }).click();
  const section = page.getByRole("region", {
    name: "Recorded evidence inspections",
  });
  await section.waitFor();
  assert.equal(commands.length, 0);
  await section
    .getByRole("button", { name: "Record an inspection", exact: true })
    .click();
  const form = page.getByRole("dialog", {
    name: "Record an inspection",
    exact: true,
  });
  await form.waitFor();
  await form.getByLabel("Passage, page or section inspected").fill("Rows 1–3");
  const observation =
    "Approval is absent in the retained rows.\nFurther inquiry is needed.";
  await form.getByLabel("What you observed").fill(observation);
  await form.getByRole("button", { name: "Save record", exact: true }).click();
  await form.getByRole("alert").waitFor();
  assert.equal(
    await form.getByLabel("What you observed").inputValue(),
    observation,
  );
  assert.equal(commands.length, 1);
  reject = false;
  await form.getByRole("button", { name: "Save record", exact: true }).click();
  await form.waitFor({ state: "hidden" });
  await section
    .getByText("Recorded inspections of this exact original · 1", {
      exact: true,
    })
    .click();
  await section.getByText("Rows 1–3", { exact: true }).waitFor();
  assert.match(await section.textContent(), /USER-1/);
  assert.equal(e.tasks[0].status, "NOT_STARTED");
  assert.equal(e.tasks[0].conclusion, "NOT_RUN");
  await page.setViewportSize({ width: 390, height: 844 });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  );
  await page.screenshot({
    path: resolve(output, "narrow.png"),
    fullPage: true,
  });
  await page.reload();
  await page.getByText("review.csv", { exact: true }).click();
  await section.waitFor();
  assert.equal(commands.length, 2);
  e.permissions = ["review"];
  await page.reload();
  await page.getByText("review.csv", { exact: true }).click();
  assert.equal(
    await section
      .getByRole("button", { name: "Record an inspection", exact: true })
      .count(),
    0,
  );
  e.capabilities = {};
  await page.reload();
  await page.getByText("review.csv", { exact: true }).click();
  assert.equal(await section.count(), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(unexpected, []);
  const html = await readFile("dist/index.html");
  const assets = {};
  for (const match of html
    .toString()
    .matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g))
    assets[match[1]] = createHash("sha256")
      .update(await readFile("dist" + match[1]))
      .digest("hex");
  await writeFile(
    resolve(output, "PASS.json"),
    JSON.stringify(
      {
        qualification: "COMPILED_APP_NEUTRAL_PROJECTIONS_NOT_REAL_AUDIT",
        commands: commands.length,
        checks: [
          "explicit authored submission",
          "exact frozen pins",
          "empty optional task omitted",
          "error preserves text",
          "attributed record visible",
          "tasks unchanged",
          "reload no automatic record",
          "reviewer and old capability gated",
          "390px",
        ],
        assets,
      },
      null,
      2,
    ),
  );
  console.log("PASS explicit inspection compiled application journey");
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
