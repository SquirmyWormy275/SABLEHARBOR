import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";
const base = "http://127.0.0.1:8847",
  server = spawn(
    process.execPath,
    [
      "node_modules/vite/bin/vite.js",
      "--host",
      "127.0.0.1",
      "--port",
      "8847",
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
  const page = await browser.newPage(),
    calls = [],
    errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const pin = "a".repeat(64),
    e = {
      id: "E",
      revision: 3,
      permissions: ["instruct"],
      scope: { boundaries: ["B"] },
      tasks: [],
      artifacts: [],
    },
    filters = {
      query: "SYS",
      issue_id: null,
      scope_to_issue: false,
      source: null,
      page: 0,
    };
  let rows = [],
    lost = true,
    hold = false,
    releaseHold,
    conflict = false,
    redact = false;
  const index = {
    status: "UNBOUND_REFERENCE_LIBRARY",
    binding: { status: "NOT_BOUND", engagement_id: "E" },
    archive: { sha256: pin },
    audience: "INSTRUCTOR_ONLY",
    required: 1110,
    migrated: 1110,
    entries: Array.from({ length: 1110 }, (_, i) => ({
      id: `SEL.O${i}.V1`,
      raw_sha256: pin,
      canonical_sha256: pin,
      key_sha256: pin,
      review: {
        professional: "UNVALIDATED",
        causal_validation: "UNVALIDATED",
        grading: "NOT_PERFORMED",
        gaps: [],
      },
    })),
  };
  await page.route("**/__keyviews", (r) =>
    r.fulfill({
      contentType: "text/html",
      body: `<div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;const rm=await import('/node_modules/.vite/deps/react.js');const React=rm.default??rm;const cm=await import('/node_modules/.vite/deps/react-dom_client.js');const root=(cm.createRoot??cm.default.createRoot)(document.getElementById('root'));const {InstructorKeyViews}=await import('/src/InstructorKeyViews.tsx');const {default:InstructorKey}=await import('/src/InstructorKey.tsx');window.e=${JSON.stringify(e)};window.filters=${JSON.stringify(filters)};window.mode='BOUND';window.actor='T';window.restores=[];window.render=()=>root.render(React.createElement(React.StrictMode,null,window.mode==='ARCHIVE'?React.createElement(InstructorKey,{engagement:window.e,viewerId:window.actor,savedViewsEnabled:true}):React.createElement(InstructorKeyViews,{engagement:window.e,viewerId:window.actor,enabled:true,kind:'BOUND',keyPin:'${pin}',filters:window.filters,validate:v=>v,onRestore:v=>{window.restores.push(v);window.filters=v;window.render();}})));window.render();</script>`,
    }),
  );
  await page.route("**/api/**", async (route) => {
    const req = route.request(),
      url = new URL(req.url()),
      path = url.pathname,
      body = req.postDataJSON();
    calls.push({ path, method: req.method(), body });
    let value;
    if (path.endsWith("/instructor-key")) value = index;
    else if (req.method() === "GET") {
      const kind = url.searchParams.get("kind");
      value = {
        engagement_id: "E",
        current_engagement_revision: 3,
        kind,
        views: rows
          .filter((r) => r.kind === kind)
          .map((r) =>
            redact
              ? {
                  ...r,
                  personal_content_visible: false,
                  restorable: false,
                  context_status: "KEY_CHANGED",
                  user: undefined,
                  key_pin: undefined,
                }
              : r,
          ),
      };
      if (hold) {
        hold = false;
        await new Promise((resolve) => (releaseHold = resolve));
      }
    } else if (path.endsWith("/restore")) {
      const row = rows.find((r) => path.includes("/" + r.id + "/"));
      value = { ...row, navigation: row.user };
    } else if (path.endsWith("/delete")) {
      const row = rows.find((r) => path.includes("/" + r.id + "/"));
      rows = rows.filter((r) => r.id !== row.id);
      const { user, key_pin, ...other } = row;
      value = {
        ...other,
        version: row.version + 1,
        status: "DELETED",
        restorable: false,
        personal_content_visible: false,
      };
    } else {
      if (conflict) {
        conflict = false;
        return route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({ error: "Concurrent saved view change" }),
        });
      }
      const old = rows.find((r) => r.id === body.view_id);
      value = {
        id: old?.id ?? "V" + (body.kind === "BOUND" ? "B" : "A"),
        engagement_id: "E",
        kind: body.kind,
        version: (old?.version ?? 0) + 1,
        status: "ACTIVE",
        saved_engagement_revision: 3,
        current_engagement_revision: 3,
        context_status: "CURRENT",
        revision_status: "MATCHING_REVISION",
        restorable: true,
        personal_content_visible: true,
        navigation: null,
        user: body.user,
        key_pin: body.key_pin,
      };
      rows = [...rows.filter((r) => r.id !== value.id), value];
      if (lost) {
        lost = false;
        return route.abort("failed");
      }
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(value),
    });
  });
  await page.goto(base + "/__keyviews");
  await page.getByText("Saved Key views", { exact: true }).click();
  assert.equal(calls.length, 0);
  await page
    .getByLabel("Saved Key view name", { exact: true })
    .fill("Bound private filter");
  await page
    .getByRole("button", { name: "Save current Key view", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Retry exact saved Key view request" })
    .click();
  const saves = calls.filter(
    (c) =>
      c.method === "POST" &&
      !c.path.endsWith("/restore") &&
      !c.path.endsWith("/delete"),
  );
  assert.deepEqual(saves[0].body, saves[1].body);
  assert.equal((await page.evaluate(() => window.restores)).length, 0);
  await page.evaluate(() => {
    window.filters = { ...window.filters, query: "new unsaved query" };
    window.render();
  });
  await page
    .getByRole("button", { name: "Restore Key view VB", exact: true })
    .waitFor();
  assert(
    await page
      .getByRole("button", { name: "Restore Key view VB", exact: true })
      .isDisabled(),
  );
  await page
    .getByLabel(
      "Allow explicit restore to replace my current unsaved Key filters and name",
    )
    .check();
  await page
    .getByRole("button", { name: "Restore Key view VB", exact: true })
    .click();
  await page
    .getByText("Exact saved filters restored.", { exact: false })
    .waitFor();
  assert.equal((await page.evaluate(() => window.filters)).query, "SYS");
  conflict = true;
  await page
    .getByLabel("Saved Key view name", { exact: true })
    .fill("Keep after conflict");
  await page
    .getByRole("button", { name: "Save current Key view", exact: true })
    .click();
  await page.getByRole("alert").filter({ hasText: "Concurrent" }).waitFor();
  assert.equal(
    await page.getByLabel("Saved Key view name", { exact: true }).inputValue(),
    "Keep after conflict",
  );
  redact = true;
  await page.getByRole("button", { name: "Load saved Key views" }).click();
  await page.getByText("KEY_CHANGED", { exact: false }).waitFor();
  assert.equal(
    await page.getByRole("heading", { name: "Bound private filter" }).count(),
    0,
  );
  redact = false;
  hold = true;
  await page.getByRole("button", { name: "Load saved Key views" }).click();
  while (!releaseHold) await delay(10);
  await page.evaluate(() => {
    window.actor = "OTHER";
    window.render();
  });
  releaseHold();
  await delay(100);
  assert.equal(
    await page.getByRole("heading", { name: "Bound private filter" }).count(),
    0,
  );
  // Real archive explorer integration against full-size1110-entry index.
  await page.evaluate(() => {
    window.actor = "T";
    window.mode = "ARCHIVE";
    window.render();
  });
  await page.getByText("Saved Key views", { exact: true }).click();
  await page.getByLabel("Search source ID or review gap").fill("SEL.O100");
  await page
    .getByLabel("Saved Key view name", { exact: true })
    .fill("Archive search");
  await page
    .getByRole("button", { name: "Save current Key view", exact: true })
    .click();
  await page.getByRole("heading", { name: "Archive search" }).waitFor();
  await page.getByLabel("Search source ID or review gap").fill("SEL.O200");
  await page
    .getByLabel(
      "Allow explicit restore to replace my current unsaved Key filters and name",
    )
    .check();
  await page
    .getByRole("button", { name: "Restore Key view VA", exact: true })
    .click();
  await page
    .getByText("Exact saved filters restored.", { exact: false })
    .waitFor();
  assert.equal(
    await page.getByLabel("Search source ID or review gap").inputValue(),
    "SEL.O100",
  );
  assert(
    !calls.some(
      (c) =>
        c.path.match(/instructor-key\//) ||
        c.path.includes("/content") ||
        c.path.includes("comparison"),
    ),
  );
  await page
    .getByRole("button", { name: "Delete Key view VA", exact: true })
    .click();
  await page.getByText("Saved Key view deleted;", { exact: false }).waitFor();
  assert.equal(
    await page.getByLabel("Search source ID or review gap").inputValue(),
    "SEL.O100",
  );
  const count = calls.length;
  await page.evaluate(() => {
    window.e = { ...window.e, permissions: ["learn"] };
    window.render();
  });
  await delay(100);
  assert.equal(
    await page.getByText("Saved Key views", { exact: true }).count(),
    0,
  );
  assert.equal(calls.length, count);
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        "both strict variants",
        "exact lost-save retry",
        "unsaved-filter explicit replacement",
        "409 preserves title",
        "changed Key redacts title/query",
        "late old-principal response discarded",
        "1110-entry real archive mount",
        "no automatic detail/original/comparison fetch",
        "delete preserves current filters",
        "learner no requests or Key view DOM",
      ],
    }),
  );
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
