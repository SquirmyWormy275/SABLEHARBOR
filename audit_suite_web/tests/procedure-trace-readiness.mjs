import { chromium } from "@playwright/test";
import { build } from "esbuild";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import assert from "node:assert/strict";
const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const pin = "a".repeat(64);
const e = {
  id: "E",
  revision: 7,
  scope: { boundaries: ["corporate"] },
  permissions: ["learn"],
  controls: [{ id: "C", title: "Local control" }],
  tasks: [{ id: "T" }],
  requests: [],
  artifacts: [],
  populations: [],
  selections: [],
  reviews: [],
  workpapers: [
    {
      id: "W",
      version: 2,
      versions: [
        { version: 1, text: "Historical exact text" },
        { version: 2, text: "Current separate text" },
      ],
    },
  ],
  sample_execution_inputs: {
    status: "AVAILABLE",
    engagement_id: "E",
    engagement_revision: 7,
    workpaper_versions: [
      { workpaper_id: "W", workpaper_version: 1, workpaper_digest: pin },
      {
        workpaper_id: "W",
        workpaper_version: 2,
        workpaper_digest: "b".repeat(64),
      },
    ],
  },
};
const ref = { kind: "workpaper", id: "W", version: 1, sha256: pin };
const trace = {
  id: "OLD",
  revision: 1,
  status: "EXACT_VISIBLE_METADATA_LINKS",
  reason_codes: [],
  exact_refs: [ref],
  recorded_item_status_counts: { SUPPORT_UNAVAILABLE: 1 },
  selected_item_count: 2,
  items_with_no_recorded_observation_count: 1,
  population_reliability: {
    recorded_status: "PROVISIONAL",
    selection_provisional: true,
    current_population_status: "PROVISIONAL",
    current_selection_provisional: true,
  },
  period_qualification: {
    declared_population_scope: {
      period_start: "2027-01-01",
      period_end: "2027-01-04",
    },
    source_query: "Explicit local supplied rows",
    completeness_representation: "Authored declaration only",
  },
};
const traceReport = {
  status: "RECORDED_TRACE_LINKS",
  trace_count: 2,
  current_leaf_count: 1,
  current_leaf_item_status_counts: { OBSERVED: 1 },
  lineages: [
    {
      root_id: "OLD",
      current_leaf_id: "NEW",
      historical_trace_ids: ["OLD"],
      status: "EXACT_VISIBLE_METADATA_LINKS",
    },
  ],
  traces: [
    trace,
    {
      ...trace,
      id: "NEW",
      revision: 2,
      exact_refs: [{ ...ref, version: 2, sha256: "b".repeat(64) }],
      recorded_item_status_counts: { OBSERVED: 1 },
    },
  ],
};
const report = {
  engagement_id: "E",
  engagement_revision: 7,
  denominators: {
    scoped_controls: 1,
    scoped_procedures: 1,
    unassigned_or_out_of_scope_tasks: 0,
    known_not_applicable_tasks: 0,
  },
  limits: ["Recorded metadata only"],
  controls: [
    {
      control: { id: "C" },
      procedure_denominator: 1,
      reasons: [],
      sources: [],
      procedures: [
        {
          task: { kind: "task", id: "T" },
          recorded_status: "NOT_STARTED",
          recorded_conclusion: "NOT_ASSESSED",
          sample_trace_readiness: traceReport,
        },
      ],
    },
  ],
};
const entry = `import React from 'react';import{createRoot}from'react-dom/client';import{WorkStatus}from'./src/WorkStatus';const root=createRoot(document.getElementById('root'));window.e=${JSON.stringify(e)};window.opened=[];window.render=()=>root.render(React.createElement(WorkStatus,{engagement:window.e,onPreview:(kind,row,reference)=>window.opened.push({kind,id:row.id,reference})}));window.render();`;
const built = await build({
  stdin: { contents: entry, resolveDir: web, loader: "tsx" },
  write: false,
  bundle: true,
  format: "esm",
  platform: "browser",
  jsx: "automatic",
  resolveExtensions: [".ts", ".tsx", ".js"],
});
const css = await readFile(web + "/src/style.css");
const browser = await chromium.launch({
  headless: true,
  executablePath: "/usr/bin/chromium",
});
try {
  const page = await browser.newPage();
  const errors = [];
  let variant = "normal",
    release,
    started;
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", async (route) => {
    const req = route.request(),
      path = new URL(req.url()).pathname;
    assert.equal(req.method(), "GET");
    if (path === "/entry.js")
      return route.fulfill({
        contentType: "text/javascript",
        body: Buffer.from(built.outputFiles[0].contents),
      });
    if (path === "/style.css")
      return route.fulfill({ contentType: "text/css", body: css });
    if (path === "/")
      return route.fulfill({
        contentType: "text/html",
        body: '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/style.css"></head><body><main class="workspace" id="root"></main><script type="module" src="/entry.js"></script></body></html>',
      });
    if (path.endsWith("/work-status")) {
      const body = structuredClone(report);
      if (variant === "wrong") body.engagement_id = "OTHER";
      if (variant === "unavailable") {
        Object.assign(body.controls[0].procedures[0].sample_trace_readiness, {
          status: "UNAVAILABLE",
          current_leaf_count: null,
          current_leaf_item_status_counts: null,
          traces: [
            {
              id: "BAD",
              status: "UNAVAILABLE",
              reason_codes: ["ARTIFACT_PIN_UNAVAILABLE"],
            },
          ],
          lineages: [
            {
              root_id: "BAD",
              current_leaf_id: null,
              status: "UNAVAILABLE",
              historical_trace_ids: [],
            },
          ],
        });
      }
      if (variant === "hold") {
        started?.();
        await new Promise((r) => (release = r));
      }
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    }
    throw Error("Unexpected request " + path);
  });
  await page.goto("http://trace.invalid/");
  await page
    .getByText("Recorded work and open dependencies", { exact: true })
    .click();
  const check = () =>
    page
      .getByRole("button", { name: "Check work status", exact: true })
      .click();
  const open = async () => {
    await page.getByLabel("Inspect control status").selectOption("C");
    await page
      .getByText("Exact procedure and source records", { exact: true })
      .click();
  };
  await check();
  await open();
  await page
    .getByText("Retained traces: 2 · Current correction lineages: 1", {
      exact: true,
    })
    .waitFor();
  await page.getByText(/Historical retained trace · OLD/).click();
  await page
    .getByRole("button", {
      name: "Open exact workpaper W · version 1",
      exact: true,
    })
    .click();
  assert.deepEqual(await page.evaluate(() => window.opened), [
    { kind: "workpaper", id: "W", reference: ref },
  ]);
  await page
    .getByText("Population reliability and period qualifications", {
      exact: true,
    })
    .first()
    .click();
  await page
    .getByText("Explicit local supplied rows", { exact: true })
    .first()
    .waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  );
  variant = "unavailable";
  await check();
  await open();
  await page
    .getByText(
      "Retained traces: 2 · Current correction lineages: Unavailable",
      { exact: true },
    )
    .waitFor();
  await page
    .getByText("Disposition counts unavailable. This is not a zero count.", {
      exact: true,
    })
    .waitFor();
  assert.equal(
    await page.getByRole("button", { name: /Open exact workpaper/ }).count(),
    0,
  );
  variant = "wrong";
  await check();
  await page.getByRole("alert").waitFor();
  assert.equal(await page.getByText(/Retained traces:/).count(), 0);
  variant = "hold";
  const pending = new Promise((r) => (started = r));
  await check();
  await pending;
  await page.evaluate(() => {
    window.e = { ...window.e, revision: 8 };
    window.render();
  });
  release();
  await page.waitForTimeout(100);
  assert.equal(await page.getByText(/Retained traces:/).count(), 0);
  assert.deepEqual(errors, []);
  console.log(
    "PASS WorkStatus trace UI: historical exact pin, qualifiers, null counts, denied references, wrong and late responses, narrow layout",
  );
} finally {
  await browser.close();
}
