import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";
const port = 8844,
  base = `http://127.0.0.1:${port}`,
  server = spawn(
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
    if (i === 99) throw Error("Vite unavailable");
  }
  browser = await chromium.launch({
    headless: true,
    executablePath: "/usr/bin/chromium",
  });
  for (const scenario of ["ambiguous", "external", "failed"]) {
    const page = await browser.newPage(),
      errors = [],
      posted = [];
    page.on("pageerror", (e) => errors.push(e.message));
    let state = {
        id: "E",
        revision: 1,
        phase: "ACTIVE",
        scope: { boundaries: ["corporate"] },
        permissions: ["learn"],
        requests: [
          { id: "R1", title: "Received one", unread: true },
          { id: "R2", title: "Received two", unread: true },
          { id: "R3", title: "Received three", unread: true },
          { id: "READ", title: "Already read", unread: false },
        ],
      },
      release = null;
    const receipts = new Map();
    await page.route("**/__read-batch", (route) =>
      route.fulfill({
        contentType: "text/html",
        body: `<html><body><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;const rm=await import('/node_modules/.vite/deps/react.js');const React=rm.default??rm;const cm=await import('/node_modules/.vite/deps/react-dom_client.js');const createRoot=cm.createRoot??cm.default.createRoot;const {RequestReadBatch}=await import('/src/RequestReadBatch.tsx');const root=createRoot(document.getElementById('root'));window.state=${JSON.stringify(state)};window.render=()=>root.render(React.createElement(RequestReadBatch,{engagement:window.state,viewerId:'P',onState:value=>{window.state=value;window.render()}}));window.render();</script></body></html>`,
      }),
    );
    await page.route("**/api/**", async (route) => {
      const req = route.request(),
        c = req.postDataJSON();
      assert(req.url().endsWith("/commands"));
      assert.equal(req.method(), "POST");
      assert.equal(c.kind, "pbc.read");
      assert.deepEqual(Object.keys(c.payload), ["request_id"]);
      posted.push(c);
      if (receipts.has(c.command_id))
        return route.fulfill({
          contentType: "application/json",
          body: JSON.stringify(receipts.get(c.command_id)),
        });
      assert.equal(c.expected_revision, state.revision);
      if (scenario === "failed" && c.payload.request_id === "R2")
        return route.fulfill({
          status: 403,
          contentType: "application/json",
          body: JSON.stringify({ error: "Permission changed" }),
        });
      state = {
        ...state,
        revision: state.revision + 1,
        requests: state.requests.map((r) =>
          r.id === c.payload.request_id ? { ...r, unread: false } : r,
        ),
      };
      receipts.set(c.command_id, structuredClone(state));
      if (scenario === "external" && c.payload.request_id === "R1")
        await new Promise((resolve) => {
          release = resolve;
        });
      if (scenario === "ambiguous" && c.payload.request_id === "R2")
        return route.abort("failed");
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(state),
      });
    });
    await page.goto(base + "/__read-batch");
    await page
      .getByText("Mark received requests read", { exact: true })
      .click();
    await page.getByLabel("Select request R1").check();
    await page.getByRole("button", { name: "Preview read changes" }).click();
    assert.match(
      await page
        .getByRole("region", { name: "Request read batch preview" })
        .innerText(),
      /Selected: 1/,
    );
    await page.getByLabel("Batch request filter").fill("Received");
    assert.equal(
      await page
        .getByRole("button", { name: "Confirm mark 1 requests read" })
        .isDisabled(),
      true,
    );
    await page.getByLabel("Batch request filter").fill("");
    await page.getByLabel("All currently filtered requests").check();
    await page.getByRole("button", { name: "Preview read changes" }).click();
    const preview = page.getByRole("region", {
      name: "Request read batch preview",
    });
    assert.match(
      await preview.innerText(),
      /Selected: 4 · Matched: 4 · Eligible: 3 · Excluded: 1/,
    );
    assert.match(await preview.innerText(), /READ: No unread marker/);
    assert.equal(posted.length, 0);
    await page
      .getByRole("button", { name: "Confirm mark 3 requests read" })
      .click();
    if (scenario === "external") {
      for (let i = 0; i < 100 && !release; i++) await delay(10);
      assert(release);
      await page.evaluate(() => {
        window.state = { ...window.state, revision: 2 };
        window.render();
      });
      await page
        .getByRole("alert")
        .filter({ hasText: "outside this batch" })
        .waitFor();
      release();
      await delay(150);
      assert.equal(posted.length, 1);
    } else {
      await page.getByRole("alert").waitFor();
      assert.equal(posted.length, 2);
    }
    if (scenario === "ambiguous") {
      await page
        .getByRole("button", { name: "Retry exact read command" })
        .click();
      await page
        .getByRole("alert")
        .filter({ hasText: "Exact retry confirmed" })
        .waitFor();
      assert.deepEqual(posted[1], posted[2]);
      assert.notEqual(posted[0].command_id, posted[1].command_id);
      assert.equal(posted.length, 3);
      assert.match(
        await page
          .getByRole("region", { name: "Request read batch results" })
          .innerText(),
        /2 succeeded/,
      );
    }
    if (scenario === "failed") {
      assert.equal(
        await page
          .getByRole("button", { name: "Retry exact read command" })
          .count(),
        0,
      );
      assert.match(
        await page
          .getByRole("region", { name: "Request read batch results" })
          .innerText(),
        /R2: FAILED/,
      );
    }
    assert.match(
      await page
        .getByRole("region", { name: "Request read batch results" })
        .innerText(),
      /R3: NOT_ATTEMPTED/,
    );
    assert.deepEqual(errors, []);
    await page.close();
  }
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        "explicit filtered preview counts and excluded IDs",
        "sequential administrative-only commands",
        "partial success exact ambiguous retry without following-item replay",
        "external revision stops remaining items",
        "definitive permission failure stops without retry",
      ],
    }),
  );
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
