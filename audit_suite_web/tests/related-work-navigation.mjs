// Full-App authorized-projection navigation with a 409-procedure corpus.
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";

const base = "http://127.0.0.1:8878";
const server = spawn(
  process.execPath,
  [
    "node_modules/vite/bin/vite.js",
    "--host",
    "127.0.0.1",
    "--port",
    "8878",
    "--strictPort",
  ],
  { stdio: "pipe" },
);
let browser;
try {
  for (let i = 0; i < 100; i++) {
    try {
      if ((await fetch(base)).ok) break;
    } catch {}
    await delay(100);
    if (i === 99) throw Error("Vite unavailable");
  }
  browser = await chromium.launch({
    headless: true,
    executablePath: "/usr/bin/chromium",
  });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 900 },
  });
  const errors = [],
    requests = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const e = {
    id: "E-RELATED",
    title: "Context navigation fixture",
    revision: 1,
    phase: "ACTIVE",
    discipline: "IT",
    mode: "CLEAN",
    permissions: ["learn"],
    simulated_at: "2027-01-01T00:00:00Z",
    scope: {
      programs: ["SOC2"],
      boundaries: ["corporate"],
      report_type: "TYPE2",
      period_start: "2027-01-01",
      period_end: "2027-12-31",
    },
    company_source_binding: { company: "Sable Harbor", branch: "clean" },
    evidence_acquisition: { mode: "company_source" },
    controls: [
      { id: "C1", title: "Access register", frameworks: ["SOC2"] },
      { id: "C2", title: "Other control", frameworks: ["SOC2"] },
    ],
    tasks: Array.from({ length: 409 }, (_, i) => ({
      id: `TASK:${String(i + 1).padStart(3, "0")}`,
      title: `Procedure matrix ${i + 1}`,
      control_id: "C1",
      boundary_id: "corporate",
      frameworks: ["SOC2"],
      status: "NOT_STARTED",
      conclusion: "NOT_RUN",
    })),
    requests: Array.from({ length: 12 }, (_, i) => ({
      id: `R${String(i).padStart(3, "0")}`,
      title: `Recorded request ${i}`,
      control_id: "C1",
      purpose: "Declared scope",
      status: "DRAFT",
    })),
    artifacts: [
      {
        id: "A1",
        title: "Retained company export",
        request_id: "R011",
        status: "AVAILABLE",
        mime: "text/csv",
        bytes: 0,
        sha256: "a".repeat(64),
      },
      {
        id: "A2",
        title: "Unavailable company export",
        request_id: "R011",
        status: "UNAVAILABLE",
      },
    ],
    workpapers: [
      {
        id: "W1",
        title: "Procedure workpaper",
        prepared_by: "L",
        versions: [
          {
            version: 1,
            task_ids: ["TASK:001"],
            text: "Exact first-version work",
            evidence_ids: [],
          },
          {
            version: 2,
            task_ids: [],
            text: "Unlinked successor must not substitute",
            evidence_ids: [],
          },
        ],
      },
    ],
    people: [],
    meetings: [],
    notes: [],
    populations: [],
    selections: [],
    calendar: [],
    findings: [],
    reviews: [],
    surveys: [],
    events: [],
    exports: [],
    // These are not navigated or indexed by relationship navigation.
    instructor_key: { facts: ["HIDDEN_INSTRUCTOR_ANSWER"] },
  };
  let viewer = { id: "L", display_name: "Learner", roles: ["learner"] };
  await page.route("**/api/**", (route) => {
    const req = route.request(),
      path = new URL(req.url()).pathname;
    requests.push({ method: req.method(), path });
    if (req.method() !== "GET")
      return route.fulfill({
        status: 400,
        json: { error: "Unexpected mutation" },
      });
    if (path === "/api/bootstrap")
      return route.fulfill({
        json: {
          viewer,
          csrf_token: "test",
          engagements: [{ id: e.id, title: e.title }],
          capabilities: {},
          programs: [],
          controls: [],
          people: [],
        },
      });
    if (path === `/api/engagements/${e.id}`)
      return route.fulfill({ json: structuredClone(e) });
    return route.fulfill({ status: 403, json: { error: "Unavailable" } });
  });

  await page.goto(`${base}/?engagement=${e.id}&view=controls`);
  const controlsSearch = page
    .getByRole("heading", { name: "Common control register" })
    .locator("xpath=following-sibling::div[1]")
    .getByRole("searchbox", { name: "Search records" });
  await controlsSearch.fill("Access");
  await page.keyboard.press("Control+k");
  const workspaceSearch = page.getByRole("searchbox", {
    name: "Search this engagement",
  });
  await workspaceSearch.fill("TASK:001");
  await page
    .getByRole("button", { name: "Search records", exact: true })
    .click();
  const openRecord = page.getByRole("button", {
    name: "Open record TASK:001",
    exact: true,
  });
  await openRecord.focus();
  await page.keyboard.press("Enter");
  let dialog = page.getByRole("dialog");
  await dialog
    .getByRole("heading", {
      name: "Related work for procedure TASK:001",
      exact: true,
    })
    .waitFor();
  const link = new URL(page.url()).searchParams;
  assert.equal(link.get("kind"), "tasks");
  assert.equal(link.get("object"), "TASK:001");
  assert.equal(
    await dialog
      .getByRole("button", { name: "Open W1 · version 1", exact: true })
      .count(),
    1,
  );
  assert.equal(
    await dialog
      .getByRole("button", { name: "Open W1 · version 2", exact: true })
      .count(),
    0,
  );
  assert.equal(
    await dialog.getByRole("button", { name: "Open A2", exact: true }).count(),
    0,
  );
  assert.equal(
    await dialog.getByText("HIDDEN_INSTRUCTOR_ANSWER", { exact: true }).count(),
    0,
  );

  await dialog
    .getByRole("button", { name: "Open W1 · version 1", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  await dialog.getByText("Exact first-version work", { exact: true }).waitFor();
  assert.equal(
    await dialog
      .getByText("Unlinked successor must not substitute", { exact: true })
      .count(),
    0,
  );
  await dialog
    .getByRole("button", { name: "Back to task TASK:001", exact: true })
    .click();
  await dialog
    .getByRole("heading", {
      name: "Related work for procedure TASK:001",
      exact: true,
    })
    .waitFor();
  await dialog
    .getByRole("button", { name: "Show more evidence requests", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Open R011", exact: true })
    .waitFor();
  await dialog
    .getByRole("searchbox", { name: "Filter related work" })
    .fill("R011");
  await dialog.getByRole("button", { name: "Open R011", exact: true }).click();
  await dialog
    .getByRole("heading", { name: "Recorded request 11", exact: true })
    .waitFor();
  await dialog
    .getByRole("button", { name: "Back to task TASK:001", exact: true })
    .click();
  assert.equal(
    await dialog
      .getByRole("searchbox", { name: "Filter related work" })
      .inputValue(),
    "R011",
    "related filter lost during exact record inspection",
  );
  await dialog
    .getByRole("searchbox", { name: "Filter related work" })
    .fill("absent-record");
  await dialog
    .getByText(
      "No related records match this filter. Reset the filter to see the recorded links.",
      { exact: true },
    )
    .waitFor();
  await dialog
    .getByRole("button", { name: "Reset related filter", exact: true })
    .click();
  await page.keyboard.press("Escape");
  await dialog.waitFor({ state: "hidden" });
  assert.equal(await controlsSearch.inputValue(), "Access");

  const proceduresTable = page
    .locator("main.workspace > .record-table")
    .first();
  await proceduresTable
    .getByRole("searchbox", { name: "Search records" })
    .fill("Procedure matrix 40");
  await proceduresTable
    .getByRole("button", { name: "Sort by Procedure", exact: true })
    .click();
  await proceduresTable
    .getByRole("button", { name: "Inspect procedure TASK:400", exact: true })
    .click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByRole("button", { name: "Next record", exact: true })
    .click();
  await dialog
    .getByRole("heading", { name: "Procedure matrix 401", exact: true })
    .waitFor();
  await page.keyboard.press("Escape");
  assert.equal(
    await page
      .locator("main.workspace > .record-table")
      .first()
      .getByRole("searchbox", { name: "Search records" })
      .inputValue(),
    "Procedure matrix 40",
  );
  assert.equal(await workspaceSearch.inputValue(), "TASK:001");
  await page.goBack();
  await page
    .getByRole("heading", { name: "Common control register" })
    .waitFor();
  assert.equal(new URL(page.url()).searchParams.has("object"), false);
  assert.equal(await controlsSearch.inputValue(), "Access");

  // Reloadable exact procedure destination; no selection/grade side effects.
  await page.goto(
    `${base}/?engagement=${e.id}&view=controls&kind=tasks&object=TASK%3A001`,
  );
  dialog = page.getByRole("dialog");
  await dialog
    .getByRole("heading", {
      name: "Related work for procedure TASK:001",
      exact: true,
    })
    .waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  await dialog.getByRole("button", { name: "Open C1", exact: true }).click();
  await dialog
    .getByRole("heading", { name: "Related work for control C1", exact: true })
    .waitFor();
  await dialog
    .getByRole("searchbox", { name: "Filter related work" })
    .fill("TASK:409");
  const last = dialog.getByRole("button", {
    name: "Open TASK:409",
    exact: true,
  });
  await last.focus();
  await page.keyboard.press("Enter");
  await dialog
    .getByRole("heading", { name: "Procedure matrix 409", exact: true })
    .waitFor();
  assert.ok(
    await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
    "narrow dialog overflows horizontally",
  );
  await mkdir("/tmp/sableharbor-related-navigation-20261001", {
    recursive: true,
  });
  await page.screenshot({
    path: "/tmp/sableharbor-related-navigation-20261001/narrow.png",
  });
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
    "narrow page overflows horizontally",
  );
  await page.keyboard.press("Tab");
  assert.ok(
    await page.evaluate(
      () => !!document.activeElement?.closest("dialog[open]"),
    ),
    "keyboard focus escaped inspector",
  );

  // Changing source context invalidates retained relationship navigation; no old filter/links carry forward.
  e.company_source_binding = { company: "Sable Harbor", branch: "messy" };
  e.revision++;
  e.workpapers = [];
  await page.evaluate(() => dispatchEvent(new PopStateEvent("popstate")));
  await dialog
    .getByRole("heading", {
      name: "Related work for procedure TASK:001",
      exact: true,
    })
    .waitFor();
  assert.equal(
    await dialog
      .getByRole("searchbox", { name: "Filter related work" })
      .inputValue(),
    "",
  );
  assert.equal(
    await dialog.getByRole("button", { name: /Open W1/ }).count(),
    0,
  );

  // The only authority is the fetch for the selected engagement.
  await page.goto(
    `${base}/?engagement=OTHER&view=controls&kind=tasks&object=TASK%3A001`,
  );
  await page.getByRole("alert").waitFor();
  assert.equal(await page.getByRole("dialog").count(), 0);
  assert.equal(
    await page.getByRole("heading", { name: /Related work for/ }).count(),
    0,
  );
  assert.deepEqual(errors, []);
  assert.ok(
    requests.every((r) => r.method === "GET"),
    "navigation mutated domain work",
  );
  assert.ok(
    requests.every((r) =>
      [
        "/api/bootstrap",
        `/api/engagements/${e.id}`,
        "/api/engagements/OTHER",
      ].includes(r.path),
    ),
    "navigation fetched Key, source originals or other API",
  );
  console.log(
    JSON.stringify({
      status: "PASS",
      procedures: 409,
      requests: requests.length,
      mutations: 0,
      checks: [
        "exact procedure deep link",
        "exact workpaper version",
        "related filter return",
        "list/search/browser-back retention",
        "keyboard and 390px navigation",
        "source reset",
        "denied engagement",
        "no Key/original requests",
      ],
    }),
  );
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
