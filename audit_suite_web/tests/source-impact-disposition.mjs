import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";
const base = "http://127.0.0.1:8849",
  server = spawn(
    process.execPath,
    [
      "node_modules/vite/bin/vite.js",
      "--host",
      "127.0.0.1",
      "--port",
      "8849",
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
    errors = [],
    calls = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const pin = "a".repeat(64),
    other = "b".repeat(64),
    e = {
      id: "E",
      revision: 2,
      scope: { boundaries: ["B"] },
      permissions: ["learn"],
      simulated_at: "2027-01-01T09:00:00Z",
      artifacts: [{ id: "A", sha256: pin }],
      source_impact_dispositions: [],
    };
  const inputs = {
    engagement_id: "E",
    engagement_revision: 2,
    artifact_id: "A",
    comparison: {
      sha256: pin,
      artifact_id: "A",
      collected_sha256: pin,
      latest_visible_sha256: other,
      collected_version: 1,
      latest_visible_version: 2,
      simulated_as_of: "2027-01-01T09:00:00Z",
    },
    observed: {
      discovered_at: "2027-01-01T09:00:00Z",
      rechecked_at: "2027-01-01T09:00:01Z",
    },
    targets: [
      {
        sha256: pin,
        record_sha256: pin,
        reference: { id: "WP", collection: "workpapers", version: 1 },
      },
    ],
    retests: [
      {
        sha256: other,
        record_sha256: other,
        reference: { id: "TRACE", collection: "sample_executions", version: 1 },
      },
    ],
    predecessors: [],
  };
  let lost = true,
    conflict = false,
    hold = false,
    release;
  await page.route("**/__disposition", (r) =>
    r.fulfill({
      contentType: "text/html",
      body: `<div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;const rm=await import('/node_modules/.vite/deps/react.js');const React=rm.default??rm;const cm=await import('/node_modules/.vite/deps/react-dom_client.js');const root=(cm.createRoot??cm.default.createRoot)(document.getElementById('root'));const {default:Editor,SourceImpactDispositionHistory:History}=await import('/src/SourceImpactDisposition.tsx');window.e=${JSON.stringify(e)};window.enabled=true;window.render=()=>root.render(React.createElement(React.StrictMode,null,React.createElement(Editor,{engagement:window.e,viewerId:'L',artifactId:'A',enabled:window.enabled,onState:s=>{window.accepted=s;window.e=s;window.render();}}),React.createElement(History,{engagement:window.e,enabled:window.enabled})));window.render();</script>`,
    }),
  );
  await page.route("**/api/**", async (r) => {
    const req = r.request(),
      body = req.postDataJSON();
    calls.push({ url: req.url(), method: req.method(), body });
    if (req.method() === "GET") {
      if (hold) {
        hold = false;
        await new Promise((resolve) => (release = resolve));
      }
      return r.fulfill({ json: inputs });
    }
    if (conflict)
      return r.fulfill({
        status: 409,
        json: { error: "Current revision changed" },
      });
    if (lost) {
      lost = false;
      return r.abort("failed");
    }
    return r.fulfill({
      json: {
        ...e,
        revision: 3,
        source_impact_dispositions: [
          {
            id: "D",
            revision: 3,
            version: 1,
            actor: "L",
            recorded_at: "2027-01-01T09:00:02Z",
            context_status: "CURRENT",
            personal_content_visible: true,
            ...body.payload,
            comparison: inputs.comparison,
            observed: inputs.observed,
            target: inputs.targets[0],
            retest: body.payload.retest_sha256 ? inputs.retests[0] : null,
          },
        ],
      },
    });
  });
  await page.goto(base + "/__disposition");
  await page
    .getByText("Record reassessment disposition", { exact: true })
    .waitFor();
  assert.equal(calls.length, 0);
  await page
    .getByText("Record reassessment disposition", { exact: true })
    .click();
  await page
    .getByRole("button", { name: "Load current exact choices" })
    .click();
  await page.getByLabel("Affected work", { exact: true }).selectOption(pin);
  await page
    .getByLabel("Disposition", { exact: true })
    .selectOption("RETEST_LINKED");
  await page
    .getByLabel("Existing reassessment work", { exact: true })
    .selectOption(other);
  await page
    .getByLabel("Reassessment rationale", { exact: true })
    .fill("Exact later original may affect prior work.");
  await page
    .getByLabel("Intended reassessment action", { exact: true })
    .fill("Inspect linked trace; no pass asserted.");
  await page
    .getByRole("button", { name: "Save disposition", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Retry exact disposition command" })
    .click();
  await page.waitForFunction(() => window.accepted?.revision === 3);
  const posts = calls.filter((c) => c.method === "POST");
  assert.equal(posts.length, 2);
  assert.deepEqual(posts[0].body, posts[1].body);
  assert.equal(posts[0].body.payload.retest_sha256, other);
  await page
    .getByText("Recorded reassessment dispositions (1)", { exact: true })
    .click();
  await page
    .getByText("Exact later original may affect prior work.", { exact: true })
    .waitFor();
  await page.evaluate(() => {
    window.e = {
      ...window.e,
      source_impact_dispositions: window.e.source_impact_dispositions.map(
        (r) => ({
          ...r,
          context_status: "CONTEXT_CHANGED",
          personal_content_visible: false,
        }),
      ),
    };
    window.render();
  });
  await page
    .getByText("Disposition details unavailable in this current context.", {
      exact: true,
    })
    .waitFor();
  assert.equal(
    await page
      .getByText("Exact later original may affect prior work.", { exact: true })
      .count(),
    0,
  );
  await page.evaluate((e) => {
    window.e = e;
    window.render();
  }, e);
  await page
    .getByText("Record reassessment disposition", { exact: true })
    .click();
  await page
    .getByRole("button", { name: "Load current exact choices" })
    .click();
  await page.getByLabel("Affected work", { exact: true }).selectOption(pin);
  await page
    .getByLabel("Reassessment rationale", { exact: true })
    .fill("Retain this local reason");
  await page
    .getByLabel("Intended reassessment action", { exact: true })
    .fill("Inspect again");
  conflict = true;
  await page
    .getByRole("button", { name: "Save disposition", exact: true })
    .click();
  await page
    .getByRole("alert")
    .filter({ hasText: "Current revision changed" })
    .waitFor();
  await page
    .getByRole("button", { name: "Load current exact choices" })
    .click();
  assert.equal(
    await page
      .getByLabel("Reassessment rationale", { exact: true })
      .inputValue(),
    "Retain this local reason",
  );
  hold = true;
  await page
    .getByRole("button", { name: "Load current exact choices" })
    .click();
  await page.waitForTimeout(50);
  await page.evaluate(() => {
    window.e = { ...window.e, revision: 9 };
    window.render();
  });
  release();
  await delay(100);
  assert.equal(
    await page.getByLabel("Affected work", { exact: true }).count(),
    0,
  );
  await page.evaluate(() => {
    window.e = { ...window.e, permissions: ["review"] };
    window.render();
  });
  assert.equal(
    await page
      .getByText("Record reassessment disposition", { exact: true })
      .count(),
    0,
  );
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        "explicit load only",
        "exact historical target/retest",
        "ambiguous exact retry",
        "409 preserves authored form",
        "late revision response discarded",
        "unsupported role hidden",
        "history exact pins and stale content redaction",
      ],
    }),
  );
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
