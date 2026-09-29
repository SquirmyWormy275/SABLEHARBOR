import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";
const port = Number(process.env.IMPACT_TEST_PORT || 8839),
  base = `http://127.0.0.1:${port}`;
const child = spawn(
  process.execPath,
  [
    "node_modules/vite/bin/vite.js",
    "--host",
    "127.0.0.1",
    "--port",
    String(port),
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
    if (i === 99) throw Error("Vite not ready");
  }
  browser = await chromium.launch({
    headless: true,
    executablePath: "/usr/bin/chromium",
  });
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const hash = "a".repeat(64),
    anchor = {
      field: "text",
      start: 0,
      end: 7,
      excerpt: "Earlier",
      offset_unit: "UNICODE_CODEPOINT",
    };
  const state = {
    id: "E",
    revision: 1,
    simulated_at: "2027-12-31",
    permissions: ["learn"],
    scope: {},
    artifacts: [{ id: "A", sha256: hash }],
    workpapers: [
      {
        id: "W",
        versions: [
          { version: 1, text: "Earlier text", evidence_ids: ["A"] },
          { version: 2, text: "Later text", evidence_ids: [] },
        ],
      },
    ],
    reviews: [
      {
        id: "R",
        kind: "HUMAN",
        workpaper_id: "W",
        workpaper_version: 1,
        workpaper_version_digest: hash,
        anchor,
      },
    ],
    findings: [
      {
        id: "F",
        evidence_ids: [],
        remediations: [{ id: "M", evidence_ids: ["A"] }],
      },
    ],
    tasks: [],
    selections: [],
    populations: [],
    sample_executions: [
      {
        id: "X",
        revision: 1,
        predecessor_id: null,
        items: [
          {
            item_id: "I",
            observation: "Retained first item observation",
            status: "OBSERVED",
            evidence: [{ artifact_id: "A", sha256: hash }],
          },
        ],
      },
    ],
  };
  const refs = [
    {
      id: "X",
      collection: "sample_executions",
      version: 1,
      item_id: "I",
      artifact_sha256: hash,
      predecessor_id: null,
      successor_id: null,
      trace_status: "CURRENT_LEAF",
      context_status: "HISTORICAL_SCOPE_OR_SOURCE_CONTEXT",
      locators: ["row 3"],
    },
    {
      id: "R",
      collection: "reviews",
      workpaper_id: "W",
      version: 1,
      workpaper_version_digest: hash,
      anchor,
      version_status: "HISTORICAL",
      review_scope: "EXACT_PASSAGE",
    },
    {
      id: "F",
      collection: "findings",
      remediation_id: "M",
      reference_scope: "REMEDIATION_NOT_ORIGINAL_FINDING",
    },
  ];
  const report = {
    engagement_id: "E",
    engagement_revision: 1,
    simulated_as_of: "2027-12-31",
    compared_artifacts: 1,
    unavailable_comparisons: 0,
    started_at: "2026-09-21",
    completed_at: "2026-09-21",
    snapshot_isolation: "PER_SOURCE_OPERATION_NOT_GLOBAL",
    limitations: [],
    changes: [
      {
        artifact_id: "A",
        collected_version: 1,
        latest_visible_version: 2,
        collected_sha256: hash,
        latest_visible_sha256: "b".repeat(64),
        references: refs,
      },
    ],
  };
  await page.route("**/__impact-test", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<html><body><div id="root"></div><script type="module">
 import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;
 const rm=await import('/node_modules/.vite/deps/react.js');const React=rm.default??rm;const cm=await import('/node_modules/.vite/deps/react-dom_client.js');const createRoot=cm.createRoot??cm.default.createRoot;const {default:Impact}=await import('/src/SourceImpact.tsx');
 const root=createRoot(document.getElementById('root'));window.state=${JSON.stringify(state)};window.opened=[];window.render=()=>root.render(React.createElement(Impact,{engagement:window.state,onPreview:(kind,row,ref)=>window.opened.push({kind,id:row.id,ref})}));window.render();</script></body></html>`,
    }),
  );
  let slow = false;
  const requests = [];
  await page.route("**/api/**", async (route) => {
    requests.push([route.request().method(), route.request().url()]);
    if (slow) await delay(300);
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(report),
    });
  });
  await page.goto(base + "/__impact-test");
  await page
    .getByText("Check collected sources for changes", { exact: true })
    .click();
  await page
    .getByRole("button", { name: "Check source changes", exact: true })
    .click();
  await page
    .getByText("Inspect exact item I in trace X", { exact: true })
    .click();
  await page
    .getByText("Recorded observation: Retained first item observation", {
      exact: true,
    })
    .waitFor();
  assert.match(
    await page.locator("body").innerText(),
    /HISTORICAL_SCOPE_OR_SOURCE_CONTEXT/,
  );
  await page
    .getByRole("button", {
      name: "Open reviewed workpaper version 1",
      exact: true,
    })
    .click();
  await page
    .getByRole("button", { name: "Open review R", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Open finding F", exact: true })
    .click();
  const opened = await page.evaluate(() => window.opened);
  assert.equal(opened[0].kind, "workpaper");
  assert.equal(opened[0].ref.version, 1);
  assert.equal(opened[1].id, "R");
  assert.equal(opened[2].ref.remediation_id, "M");
  assert.match(
    await page.locator("body").innerText(),
    /REMEDIATION_NOT_ORIGINAL_FINDING/,
  );
  slow = true;
  await page
    .getByRole("button", { name: "Check source changes", exact: true })
    .click();
  await page.evaluate(() => {
    window.state = { ...window.state, revision: 2, permissions: ["review"] };
    window.render();
  });
  await delay(400);
  assert.equal(
    await page
      .getByRole("button", { name: "Open review R", exact: true })
      .count(),
    0,
  );
  assert.equal(
    await page
      .getByText("Recorded observation: Retained first item observation", {
        exact: true,
      })
      .count(),
    0,
  );
  assert(requests.every(([method]) => method === "GET"));
  assert(requests.every(([, url]) => url.endsWith("/company/impact")));
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        "Exact historical review/workpaper callback version",
        "Exact trace item details and historical context",
        "Remediation-only finding reference",
        "Stale asynchronous result hidden after context change",
        "No commands or protected-Key requests",
      ],
    }),
  );
} finally {
  await browser?.close();
  child.kill("SIGTERM");
}
