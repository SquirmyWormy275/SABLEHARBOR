import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";
const port = 8845,
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
  const page = await browser.newPage(),
    errors = [],
    requests = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const e = {
    id: "E",
    revision: 1,
    scope: { boundaries: ["corporate"] },
    permissions: ["learn"],
    work_guidance_policy: { allowed: false, version: 0 },
    controls: [{ id: "C" }],
    workpapers: [
      {
        id: "W",
        versions: [
          { version: 1, text: "Earlier assessment" },
          { version: 2, text: "Current assessment" },
        ],
      },
    ],
    tasks: [],
    requests: [],
    artifacts: [],
    populations: [],
    selections: [],
    reviews: [],
  };
  const pin = {
      kind: "control",
      id: "C",
      version: null,
      sha256: "a".repeat(64),
    },
    wp = { kind: "workpaper", id: "W", version: 1, sha256: "b".repeat(64) };
  let state = {
      engagement_id: "E",
      current_engagement_revision: 1,
      version: 0,
      policy_version: 1,
      policy_allowed: true,
      opted_in: false,
      personal_content_visible: false,
      status: "OPT_IN_REQUIRED",
      contexts: [],
    },
    lose = true,
    hold = false,
    release = null,
    oldFailure = false;
  let wrongMetadata = true;
  const candidate = {
    id: "G1",
    sha256: "c".repeat(64),
    code: "REVIEW_WORK",
    title: "Inspect the recorded workpaper",
    reason: "Visible recorded references only",
    context_ref: pin,
    references: [
      { kind: "workpaper", id: "W", status: "CURRENT", reference: wp },
    ],
  };
  await page.route("**/__guidance", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<html><body><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;const rm=await import('/node_modules/.vite/deps/react.js');const React=rm.default??rm;const cm=await import('/node_modules/.vite/deps/react-dom_client.js');const createRoot=cm.createRoot??cm.default.createRoot;const {WorkGuidance}=await import('/src/WorkGuidance.tsx');const root=createRoot(document.getElementById('root'));window.e=${JSON.stringify(e)};window.opened=[];window.commands=[];window.render=()=>root.render(React.createElement(React.StrictMode,null,React.createElement(WorkGuidance,{engagement:window.e,viewerId:'P',busy:false,onCommand:async(kind,payload)=>{window.commands.push({kind,payload});return undefined},onPreview:(kind,row,pin)=>window.opened.push({kind,id:row.id,pin})})));window.render();</script></body></html>`,
    }),
  );
  await page.route("**/api/**", async (route) => {
    const req = route.request(),
      body = req.postDataJSON(),
      path = new URL(req.url()).pathname;
    requests.push({ method: req.method(), path, body });
    let value;
    if (req.method() === "GET") {
      value = structuredClone(state);
      if (wrongMetadata) {
        wrongMetadata = false;
        value.policy_version = 0;
      }
      if (hold) {
        hold = false;
        await new Promise((resolve) => (release = resolve));
        if (oldFailure)
          return route.fulfill({
            status: 403,
            contentType: "application/json",
            body: JSON.stringify({ error: "Old denied context" }),
          });
      }
    } else if (path.endsWith("/preference")) {
      assert.equal(body.enabled, true);
      state = {
        ...state,
        version: 1,
        opted_in: true,
        personal_content_visible: true,
        status: "AVAILABLE",
        contexts: [{ reference: pin, title: "Control C" }],
      };
      value = state;
    } else if (path.endsWith("/reveal")) {
      assert.deepEqual(body.context_ref, pin);
      value = { ...state, version: 2, candidates: [candidate] };
      if (lose) {
        lose = false;
        return route.abort("failed");
      }
    } else if (path.endsWith("/decision")) {
      assert(["REVIEW", "DISMISS"].includes(body.action));
      assert(body.rationale);
      assert.equal(body.candidate_sha256, candidate.sha256);
      state = { ...state, version: 3 };
      value = state;
    } else throw Error("Unexpected guidance operation");
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(value),
    });
  });
  await page.goto(base + "/__guidance");
  await page
    .getByText("Optional guidance for recorded work", { exact: true })
    .click();
  await delay(100);
  assert.equal(requests.length, 0);
  assert.equal(
    await page
      .getByRole("button", { name: "Check my guidance preference" })
      .count(),
    0,
  );
  await page.evaluate(() => {
    window.e = {
      ...window.e,
      work_guidance_policy: { allowed: true, version: 1 },
    };
    window.render();
  });
  await page
    .getByText("Optional guidance for recorded work", { exact: true })
    .click();
  await page
    .getByRole("button", { name: "Check my guidance preference" })
    .click();
  await page
    .getByRole("alert")
    .filter({ hasText: "assistance policy changed" })
    .waitFor();
  assert.equal(
    await page
      .getByRole("button", { name: "Opt in to administrative guidance" })
      .count(),
    0,
  );
  await page
    .getByRole("button", { name: "Check my guidance preference" })
    .click();
  await page
    .getByLabel("Reason for my preference")
    .fill("I explicitly want administrative guidance.");
  await page
    .getByRole("button", { name: "Opt in to administrative guidance" })
    .click();
  await page.getByLabel("Guidance control").selectOption("C");
  await page
    .getByRole("button", { name: "Show and record guidance for this control" })
    .click();
  await page
    .getByRole("button", { name: "Retry the exact guidance request" })
    .waitFor();
  await page
    .getByRole("button", { name: "Retry the exact guidance request" })
    .click();
  await page.getByRole("heading", { name: candidate.title }).waitFor();
  const reveals = requests.filter((r) => r.path.endsWith("/reveal"));
  assert.deepEqual(reveals[0].body, reveals[1].body);
  await page.getByText("Exact context and references", { exact: true }).click();
  await page.getByRole("button", { name: "Open exact reference" }).click();
  assert.equal((await page.evaluate(() => window.opened))[0].pin.version, 1);
  assert.equal(
    await page.getByRole("button", { name: "Record my review" }).isDisabled(),
    true,
  );
  await page
    .getByLabel("My review or dismissal reason")
    .fill("I inspected the exact visible version.");
  await page.getByRole("button", { name: "Record my review" }).click();
  await page
    .getByRole("heading", { name: candidate.title })
    .waitFor({ state: "detached" });
  // A delayed success from an older revision must never reintroduce preference/content.
  hold = true;
  await page
    .getByRole("button", { name: "Check my guidance preference" })
    .click();
  for (let i = 0; i < 100 && !release; i++) await delay(10);
  assert(release);
  await page.evaluate(() => {
    window.e = { ...window.e, revision: 2 };
    window.render();
  });
  release();
  await delay(100);
  assert.equal(await page.getByLabel("Reason for my preference").count(), 0);
  // Same for a delayed authorization failure after a further policy/context switch.
  state = { ...state, current_engagement_revision: 2 };
  release = null;
  hold = true;
  oldFailure = true;
  await page
    .getByText("Optional guidance for recorded work", { exact: true })
    .click();
  await page
    .getByRole("button", { name: "Check my guidance preference" })
    .click();
  for (let i = 0; i < 100 && !release; i++) await delay(10);
  assert(release);
  await page.evaluate(() => {
    window.e = {
      ...window.e,
      work_guidance_policy: { allowed: false, version: 2 },
    };
    window.render();
  });
  release();
  await delay(100);
  assert.equal(await page.getByRole("alert").count(), 0);
  assert.equal(
    await page
      .getByRole("button", { name: "Check my guidance preference" })
      .count(),
    0,
  );
  assert.deepEqual(await page.evaluate(() => window.commands), []);
  await page.evaluate(() => {
    window.e = { ...window.e, permissions: ["instruct"] };
    window.render();
  });
  await page
    .getByText("Optional guidance for recorded work", { exact: true })
    .click();
  assert.equal(
    await page
      .getByRole("button", { name: "Allow optional work guidance" })
      .isDisabled(),
    true,
  );
  await page
    .getByLabel("Reason for policy change")
    .fill("Explicit technical instructor choice.");
  await page
    .getByRole("button", { name: "Allow optional work guidance" })
    .click();
  assert.deepEqual(await page.evaluate(() => window.commands), [
    {
      kind: "assistance.configure",
      payload: {
        work_guidance_allowed: true,
        rationale: "Explicit technical instructor choice.",
      },
    },
  ]);

  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        "StrictMode lifecycle",
        "disabled policy makes no guidance fetch",
        "explicit optin+logged reveal",
        "ambiguous reveal exact retry",
        "exact historical WP callback",
        "rationale required decision only",
        "late success/failure discarded after revision/policy change",
        "only explicit instructor policy emits a formal command",
      ],
    }),
  );
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
