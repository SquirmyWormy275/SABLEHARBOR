// Isolated component journey: preview, ambiguous response, exact retry, read-only role.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { chromium } from "@playwright/test";

const port = 8861;
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
  const page = await browser.newPage();
  const errors = [], posted = [], receipts = new Map();
  page.on("pageerror", (error) => errors.push(error.message));
  const state = {
    id: "E", revision: 4, phase: "ACTIVE", permissions: ["learn"],
    tasks: [{ id: "T", title: "Inspect collection gap", status: "NOT_STARTED", conclusion: "NOT_RUN" }],
    artifacts: [], workpapers: [], task_gaps: [],
  };
  await page.route("**/__task-gap", (route) => route.fulfill({
    contentType: "text/html",
    body: `<html><body><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;const rm=await import('/node_modules/.vite/deps/react.js');const React=rm.default??rm;const cm=await import('/node_modules/.vite/deps/react-dom_client.js');const createRoot=cm.createRoot??cm.default.createRoot;const {TaskGapPanel}=await import('/src/TaskGapPanel.tsx');const {setCSRF}=await import('/src/api.ts');setCSRF('test');const root=createRoot(document.getElementById('root'));window.state=${JSON.stringify(state)};window.render=()=>root.render(React.createElement(TaskGapPanel,{engagement:window.state,taskId:'T',viewerId:'L',onState:value=>{window.state=value;window.render()},onClose:()=>{}}));window.render();</script></body></html>`,
  }));
  await page.route("**/api/**", (route) => {
    const req = route.request();
    assert.equal(req.method(), "POST");
    assert.equal(new URL(req.url()).pathname, "/api/engagements/E/commands");
    const c = req.postDataJSON();
    posted.push(c);
    assert.equal(c.kind, "task.gap.record");
    assert.deepEqual(Object.keys(c.payload), ["task_id", "cause", "owner_id", "disposition", "narrative", "artifact_pin", "retest", "predecessor_id"]);
    if (!receipts.has(c.command_id)) {
      const next = structuredClone(state);
      next.revision = 5;
      next.task_gaps = [{ id: "GAP-1", ...c.payload, actor: "L", revision: 5,
        recorded_at: "2027-02-01T00:00:00Z",
        qualification: "AUTHOR_RECORDED_GAP_NOT_EVIDENCE_OR_AUDIT_CONCLUSION" }];
      receipts.set(c.command_id, next);
      return route.abort("failed");
    }
    return route.fulfill({ json: receipts.get(c.command_id) });
  });
  await page.goto(base + "/__task-gap");
  const panel = page.getByRole("region", { name: "Task gap record for T" });
  await panel.getByLabel("Observed gap and next step").fill("The local source did not provide a collectable clock sample for this task.");
  await panel.getByRole("button", { name: "Preview exact record" }).click();
  const preview = panel.getByLabel("Task gap preview");
  assert.match(await preview.innerText(), /No status, conclusion, or retest result is inferred/);
  assert.equal(posted.length, 0);
  await panel.getByRole("button", { name: "Record gap", exact: true }).click();
  await panel.getByRole("button", { name: "Retry exact command" }).waitFor();
  assert.equal(posted.length, 1);
  await panel.getByRole("button", { name: "Retry exact command" }).click();
  await panel.getByText("GAP-1", { exact: true }).waitFor();
  assert.equal(posted.length, 2);
  assert.equal(posted[0].command_id, posted[1].command_id);
  assert.deepEqual(posted[0], posted[1]);
  const after = await page.evaluate(() => window.state);
  assert.equal(after.tasks[0].status, "NOT_STARTED");
  assert.equal(after.tasks[0].conclusion, "NOT_RUN");
  await page.evaluate(() => { window.state.permissions = ["review"]; window.render(); });
  await panel.getByText("History remains read-only here.", { exact: false }).waitFor();
  assert.equal(await panel.getByRole("button", { name: "Preview exact record" }).count(), 0);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ status: "PASS", posts: posted.length, exact_retry: true, role_restriction: true, task_unchanged: true }));
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
