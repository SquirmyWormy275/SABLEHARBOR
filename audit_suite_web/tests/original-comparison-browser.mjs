import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import assert from "node:assert/strict";
import { setTimeout as delay } from "node:timers/promises";
const port = Number(process.env.COMPARISON_TEST_PORT || 8798),
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
  for (let n = 0; n < 100; n++) {
    try {
      if ((await fetch(base)).ok) break;
    } catch {}
    await delay(100);
    if (n === 99) throw Error("Isolated Vite not ready");
  }
  browser = await chromium.launch({
    headless: true,
    executablePath: "/usr/bin/chromium",
  });
  const page = await browser.newPage();
  page.on("pageerror", (error) => console.error(error.message));

  const left = "Original older record: quantity 1\n",
    right = "Original later record: quantity 2\n";
  const a = (id, text) => ({
    id,
    name: `Native ${id}`,
    mime: "text/plain",
    status: "AVAILABLE",
    bytes: Buffer.byteLength(text),
    sha256: createHash("sha256").update(text).digest("hex"),
  });
  const state = {
    id: "NEUTRAL-E",
    revision: 1,
    permissions: ["learn"],
    scope: { boundaries: ["corporate"] },
    artifacts: [
      a("OLD", left),
      a("NEW", right),
      { ...a("PDF", right), mime: "application/pdf" },
    ],
    company_source_binding: { branch: "local-a" },
  };
  await page.route("**/__comparison-test", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<html><head></head><body><div id="root"></div><script type="module">
 import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;
 const reactModule=await import('/node_modules/.vite/deps/react.js');const React=reactModule.default??reactModule;const client=await import('/node_modules/.vite/deps/react-dom_client.js');const createRoot=client.createRoot??client.default.createRoot;const {default:Comparison}=await import('/src/OriginalComparison.tsx');
 const root=createRoot(document.getElementById('root'));window.fixture=${JSON.stringify(state)};window.renderFixture=()=>root.render(React.createElement(Comparison,{engagement:window.fixture,viewerId:'VIEWER'}));window.renderFixture();</script></body></html>`,
    }),
  );
  let late = false,
    denied = false;
  const requested = [];
  await page.route("**/api/**", async (route) => {
    const url = route.request().url();
    requested.push(url);
    if (late) await delay(350);
    await route.fulfill({
      status: denied ? 403 : 200,
      contentType: "application/octet-stream",
      body: denied ? "Denied" : url.includes("/OLD/") ? left : right,
    });
  });
  await page.goto(base + "/__comparison-test");
  await page
    .getByRole("heading", { name: "Compare two retained originals" })
    .waitFor();
  await page.getByLabel("Left original", { exact: true }).selectOption("OLD");
  await page.getByLabel("Right original", { exact: true }).selectOption("NEW");
  await page
    .getByRole("button", { name: "Load left original", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Load right original", exact: true })
    .click();
  await page.getByLabel("Left original content", { exact: true }).waitFor();
  assert.equal(
    await page
      .getByLabel("Left original content", { exact: true })
      .textContent(),
    left,
  );
  assert.equal(
    await page
      .getByLabel("Right original content", { exact: true })
      .textContent(),
    right,
  );
  await page.evaluate(() => {
    document.getElementById("root").hidden = true;
    document.getElementById("root").hidden = false;
    window.fixture = { ...window.fixture };
    window.renderFixture();
  });
  assert.equal(
    await page.getByLabel("Left original", { exact: true }).inputValue(),
    "OLD",
  );
  await page
    .getByLabel("Left file search", { exact: true })
    .fill("no matching file");
  assert.equal(
    await page.getByLabel("Left original", { exact: true }).inputValue(),
    "OLD",
  );
  assert.equal(
    await page
      .getByLabel("Left original content", { exact: true })
      .textContent(),
    left,
  );
  await page.getByLabel("Left original content", { exact: true }).focus();
  assert.equal(
    await page.evaluate(() =>
      document.activeElement.getAttribute("aria-label"),
    ),
    "Left original content",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  );
  await page.getByLabel("Right original", { exact: true }).selectOption("PDF");
  assert.equal(
    await page
      .getByRole("button", { name: "Load right original", exact: true })
      .count(),
    0,
  );
  assert.match(
    await page
      .getByRole("link", { name: "Download right original" })
      .getAttribute("href"),
    /PDF\/download$/,
  );
  late = true;
  await page
    .getByRole("button", { name: "Load left original", exact: true })
    .click();
  await page.evaluate(() => {
    window.fixture = {
      ...window.fixture,
      company_source_binding: { branch: "changed" },
    };
    window.renderFixture();
  });
  await delay(500);
  assert.equal(
    await page.getByLabel("Left original", { exact: true }).inputValue(),
    "",
  );
  assert.equal(
    await page.getByLabel("Left original content", { exact: true }).count(),
    0,
  );
  denied = true;
  await page.getByLabel("Left original", { exact: true }).selectOption("OLD");
  await page
    .getByRole("button", { name: "Load left original", exact: true })
    .click();
  await page.getByLabel("Left original", { exact: true }).selectOption("NEW");
  await delay(500);
  assert.equal(
    await page
      .getByText("Original unavailable (403).", { exact: true })
      .count(),
    0,
  );
  assert.ok(
    requested.every(
      (url) => url.includes("/artifacts/") && url.endsWith("/download"),
    ),
  );
  assert.ok(!JSON.stringify(requested).includes("instructor"));
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        "exact-two-content-hashes",
        "explicit-selection",
        "preserved-parent-navigation",
        "keyboard-pre-focus",
        "390px-stack",
        "binary-download-only",
        "late-success-binding-clear",
        "late-denial-selection-clear",
        "only-authorized-artifact-routes",
      ],
    }),
  );
} finally {
  await browser?.close();
  child.kill("SIGTERM");
}
