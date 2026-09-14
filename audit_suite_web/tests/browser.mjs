// Public synthetic layout fixture: no hidden scenario truth or production data.
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const output = resolve("../enterprise/generated/audit-suite/build/visuals");
await mkdir(output, { recursive: true });
const server = spawn(
  process.execPath,
  ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5193"],
  { stdio: "ignore" },
);
let browser;
try {
  for (let i = 0; i < 50; i++) {
    try {
      await fetch("http://127.0.0.1:5193");
      break;
    } catch {
      await new Promise((r) => setTimeout(r, 100));
    }
  }
  browser = await chromium.launch({
    executablePath: "/usr/bin/chromium",
    headless: true,
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1050 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const e = {
    id: "ENG-LAYOUT",
    title: "Corporate shared controls · reference assessment",
    revision: 4,
    discipline: "IT",
    mode: "MESSY",
    phase: "ACTIVE",
    simulated_at: "2027-02-12T09:00:00Z",
    scope: {
      programs: ["SOC2", "HIPAA"],
      period_start: "2027-01-01",
      period_end: "2027-12-31",
      report_type: "Type 2",
      boundaries: [
        "Corporate shared services",
        "Reno primary",
        "Boise recovery",
      ],
    },
    capabilities: {
      custom_authoring: false,
      experimental_review: false,
      voice: false,
    },
    controls: Array.from({ length: 32 }, (_, i) => ({
      id: `CC-${i + 1}`,
      title: `Access authorization and quarterly review ${i + 1}`,
      framework: "SOC2",
      owner_id: "P-01",
      status: "IN_PROGRESS",
    })),
    people: [
      {
        id: "P-01",
        name: "Morgan Ellis",
        role: "Infrastructure control owner",
        department: "Operations",
      },
    ],
    tasks: [
      {
        id: "T-01",
        title: "Inspect evidence of reviewer approval",
        status: "IN_PROGRESS",
        conclusion: "OPEN",
        control_id: "CC-1",
        owner_id: "P-01",
      },
    ],
    requests: [
      {
        id: "PBC-01",
        title: "Quarterly access review population",
        status: "IN_PROGRESS",
        owner_id: "P-01",
        due_at: "2027-02-15",
      },
    ],
    artifacts: [
      {
        id: "A-01",
        filename: "access-review-population.csv",
        kind: "POPULATION",
        created_at: "2027-02-12",
        request_id: "PBC-01",
      },
    ],
    meetings: [
      {
        id: "M-01",
        title: "Infrastructure walkthrough",
        status: "OPEN",
        participant_ids: ["P-01"],
        messages: [
          {
            id: "MSG-01",
            speaker_name: "Morgan Ellis",
            role: "company",
            claim_type: "statement",
            content:
              "We can walk through the quarterly approval process. Which period and population would you like to inspect?",
          },
        ],
      },
    ],
    notes: [
      {
        id: "N-01",
        title: "Infrastructure walkthrough",
        text: "Confirm population completeness before sample selection.",
        source_message_ids: ["MSG-01"],
      },
    ],
    populations: [
      {
        id: "POP-01",
        title: "Access review population",
        row_count: 120,
        control_id: "CC-1",
        status: "AVAILABLE",
      },
    ],
    selections: [],
    calendar: [
      {
        id: "CAL-01",
        title: "Evidence follow-up",
        scheduled_at: "2027-02-15T10:00:00Z",
        status: "SCHEDULED",
      },
    ],
    findings: [
      {
        id: "F-01",
        title: "Reviewer sign-off requires follow-up",
        status: "OPEN",
        control_id: "CC-1",
        severity: "LOW",
      },
    ],
    workpapers: [
      {
        id: "W-01",
        title: "Access review test",
        status: "DRAFT",
        conclusion: "OPEN",
      },
    ],
    reviews: [],
    surveys: [],
    events: [],
  };
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        path === "/api/bootstrap"
          ? {
              viewer: {
                id: "fixture",
                display_name: "Layout fixture trainer",
                roles: ["trainer", "reviewer"],
              },
              csrf_token: "fixture",
              engagements: [e],
              capabilities: e.capabilities,
              programs: [
                { id: "SOC2", name: "SOC 2" },
                { id: "HIPAA", name: "HIPAA" },
              ],
              people: [],
              controls: [],
            }
          : e,
      ),
    });
  });
  for (const view of [
    "kickoff",
    "controls",
    "pbc",
    "meetings",
    "people",
    "populations",
    "notes",
    "calendar",
    "findings",
    "review",
  ]) {
    await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=${view}`);
    await page.locator(".workspace-footer").waitFor();
    await page.screenshot({
      path: `${output}/${view}-desktop.png`,
      fullPage: true,
    });
    if (
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      )
    )
      throw Error(`Overflow ${view}`);
  }
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=pbc`);
  await page.locator(".workspace-footer").waitFor();
  await page
    .getByRole("button", { name: "New PBC request +", exact: true })
    .click();
  await page.getByRole("dialog").waitFor();
  await page.keyboard.press("Escape");
  if (await page.getByRole("dialog").count())
    throw Error("Escape did not close dialog");
  await page.addStyleTag({
    content:
      ".rail{position:static;width:auto;min-height:0;padding:14px;display:flex;flex-wrap:wrap;gap:12px}.rail nav{display:flex;flex-wrap:wrap}.rail footer,.rail-label,.engagement-switch{display:none}.main-shell{margin-left:0}.app{display:block}.brand{width:190px}.rail nav button{padding:8px}.topbar{height:48px}",
  });
  await page.screenshot({
    path: `${output}/candidate-horizontal-workroom.png`,
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=pbc`);
  await page.locator(".workspace-footer").waitFor();
  await page.screenshot({ path: `${output}/pbc-narrow.png`, fullPage: true });
  if (
    await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)
  )
    throw Error("Narrow overflow");
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.goto("http://127.0.0.1:5193");
  await page.getByRole("button", { name: /New engagement/i }).click();
  await page.getByRole("button", { name: /Messy Authored/ }).click();
  await page.getByRole("button", { name: /Continue/ }).click();
  await page.screenshot({
    path: `${output}/configuration-desktop.png`,
    fullPage: true,
  });
  if (errors.length) throw Error(errors.join("\n"));
  await writeFile(
    `${output}/browser-receipt.json`,
    JSON.stringify(
      {
        fixture:
          "Public synthetic layout data; API mocked; not a backend acceptance claim",
        views: 10,
        desktop: [1440, 1050],
        narrow: [390, 844],
        page_errors: errors,
      },
      null,
      2,
    ),
  );
  console.log(
    "10 sections, configuration, desktop/narrow: browser checks passed",
  );
} finally {
  await browser?.close();
  server.kill();
}
