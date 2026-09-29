import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";
const port = 8841,
  base = `http://127.0.0.1:${port}`;
const server = spawn(
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
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => {
    errors.push(e.message);
    console.error(e.message);
  });
  const pin = {
    kind: "workpaper",
    id: "W",
    version: 1,
    sha256: "a".repeat(64),
  };
  const e = {
    id: "E",
    revision: 1,
    scope: { boundaries: ["corporate"] },
    permissions: ["learn"],
    controls: [],
    tasks: [],
    artifacts: [],
    populations: [],
    selections: [],
    workpapers: [
      {
        id: "W",
        title: "Original assessment",
        versions: [
          { version: 1, text: "Earlier" },
          { version: 2, text: "Later" },
        ],
      },
    ],
  };
  let current = e,
    viewer = "P",
    handoffs = [],
    posts = [],
    conflict = true,
    lose = false;
  let holdList = false,
    releaseList = null;
  await page.route("**/__handoff-test", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<html><body><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;const rm=await import('/node_modules/.vite/deps/react.js');const React=rm.default??rm;const cm=await import('/node_modules/.vite/deps/react-dom_client.js');const createRoot=cm.createRoot??cm.default.createRoot;const {InvestigationHandoffs}=await import('/src/InvestigationHandoffs.tsx');const root=createRoot(document.getElementById('root'));window.e=${JSON.stringify(e)};window.viewer='P';window.opened=[];window.render=()=>root.render(React.createElement(InvestigationHandoffs,{engagement:window.e,viewerId:window.viewer,enabled:true,selectedReference:${JSON.stringify(pin)},onPreview:(kind,row,reference)=>window.opened.push({kind,id:row.id,reference})}));window.render();</script></body></html>`,
    }),
  );
  const projection = (h) => ({
    ...h,
    current_engagement_revision: current.revision,
    acting_role: viewer === h.sender_id ? "SENDER" : "RECIPIENT",
    allowed_actions:
      h.status === "OFFERED"
        ? viewer === h.sender_id
          ? ["WITHDRAW"]
          : ["ACCEPT", "DECLINE"]
        : h.status === "ACCEPTED" && viewer === h.recipient_id
          ? ["COMPLETE"]
          : [],
  });
  await page.route("**/api/**", async (route) => {
    const r = route.request(),
      path = new URL(r.url()).pathname,
      body = r.postDataJSON();
    const reply = (value) =>
      route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(value),
      });
    if (path.endsWith("/members"))
      return reply({
        engagement_id: "E",
        engagement_revision: current.revision,
        members: [
          {
            id: viewer === "P" ? "Q" : "P",
            display_name: viewer === "P" ? "Quinn" : "Pat",
            permission: "learn",
          },
        ],
      });
    if (path.endsWith("/link")) {
      assert.equal(body.recipient_id, "Q");
      assert.equal(body.version, 1);
      return reply(pin);
    }
    if (r.method() === "GET" && path.endsWith("/handoffs")) {
      const snapshot = {
        handoffs: handoffs.map((h) => structuredClone(projection(h))),
      };
      if (holdList) {
        holdList = false;
        await new Promise((resolve) => {
          releaseList = resolve;
        });
      }
      return reply(snapshot);
    }
    if (r.method() === "POST" && path.endsWith("/handoffs")) {
      posts.push(body);
      if (conflict) {
        conflict = false;
        return route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({ error: "Workspace revision changed" }),
        });
      }
      if (!handoffs.length)
        handoffs = [
          {
            id: "H",
            version: 1,
            status: "OFFERED",
            engagement_id: "E",
            sender_id: "P",
            recipient_id: "Q",
            shared_content_visible: true,
            context_status: "CURRENT",
            content: {
              ...body.payload,
              response: "",
              response_author_id: null,
            },
          },
        ];
      if (lose) {
        lose = false;
        let holdList = false,
          releaseList = null;
        return route.abort("failed");
      }
      return reply(projection(handoffs[0]));
    }
    if (path.endsWith("/transition")) {
      const h = handoffs[0];
      assert.equal(body.expected_version, h.version);
      assert.equal(body.expected_engagement_revision, current.revision);
      if (body.action === "ACCEPT") {
        assert.equal(viewer, "Q");
        h.status = "ACCEPTED";
      } else if (body.action === "COMPLETE") {
        assert.equal(viewer, "Q");
        assert(body.response);
        h.status = "COMPLETED";
      } else throw Error("Unexpected transition");
      h.version++;
      h.content.response = body.response;
      return reply(projection(h));
    }
    throw Error("Unexpected endpoint " + path);
  });
  await page.goto(base + "/__handoff-test");
  await page.getByText("Share an investigation", { exact: true }).click();
  await page.getByLabel("Investigation recipient").selectOption("Q");
  await page
    .getByLabel("Investigation title")
    .fill("Explain the earlier source");
  await page
    .getByLabel("Investigation question")
    .fill("What does the original establish?");
  await page
    .getByLabel("Investigation next step")
    .fill("Inspect retained version one.");
  await page
    .getByRole("button", { name: "Add selected workpaper W v1" })
    .click();
  await page
    .getByRole("button", { name: "Offer investigation", exact: true })
    .click();
  await page
    .getByRole("alert")
    .filter({ hasText: "Workspace revision changed" })
    .waitFor();
  assert.equal(
    await page.getByLabel("Investigation question").inputValue(),
    "What does the original establish?",
  );
  await page
    .getByRole("button", { name: "Refresh and review current workspace" })
    .click();
  await page
    .getByRole("button", { name: "Add selected workpaper W v1" })
    .click();
  lose = true;
  await page
    .getByRole("button", { name: "Offer investigation", exact: true })
    .click();
  await page.getByRole("button", { name: "Retry exact submission" }).waitFor();
  await page.getByRole("button", { name: "Retry exact submission" }).click();
  await page.getByText("Awaiting Q's decision", { exact: false }).waitFor();
  assert.deepEqual(posts[1], posts[2]);
  await page.getByRole("button", { name: "Open exact workpaper" }).click();
  assert.equal(
    (await page.evaluate(() => window.opened))[0].reference.version,
    1,
  );
  viewer = "Q";
  current = { ...current, permissions: ["review"] };
  await page.evaluate((e) => {
    window.e = e;
    window.viewer = "Q";
    window.render();
  }, current);
  await page
    .getByRole("button", { name: "Accept investigation", exact: true })
    .click();
  await page.getByText("Your response is awaited", { exact: false }).waitFor();
  await page
    .getByLabel("Response for H")
    .fill("The older version establishes only the recorded condition.");
  await page.getByRole("button", { name: "Send completion response" }).click();
  await page
    .getByText("Coordination response completed", { exact: false })
    .waitFor();
  assert.match(
    await page.locator("body").innerText(),
    /does not complete testing/,
  );
  const visibleCompleted = structuredClone(handoffs[0]);
  handoffs[0] = {
    ...handoffs[0],
    context_status: "PARTICIPANT_UNAVAILABLE",
    shared_content_visible: false,
  };
  delete handoffs[0].content;
  await page
    .getByRole("button", { name: "Refresh and review current workspace" })
    .click();
  await page.getByText("PARTICIPANT_UNAVAILABLE:", { exact: false }).waitFor();
  assert.equal(
    await page
      .getByText("What does the original establish?", { exact: true })
      .count(),
    0,
  );
  assert.equal(
    await page.getByRole("button", { name: "Open exact workpaper" }).count(),
    0,
  );
  handoffs[0] = visibleCompleted;
  await page
    .getByRole("button", { name: "Refresh and review current workspace" })
    .click();
  await page.getByRole("button", { name: "Open exact workpaper" }).waitFor();
  holdList = true;
  await page
    .getByRole("button", { name: "Refresh and review current workspace" })
    .click();
  for (let i = 0; i < 100 && !releaseList; i++) await delay(10);
  assert(releaseList);
  current = { ...current, scope: { boundaries: ["other"] }, revision: 2 };
  handoffs[0] = {
    ...handoffs[0],
    context_status: "CONTEXT_CHANGED",
    shared_content_visible: false,
  };
  delete handoffs[0].content;
  await page.evaluate((e) => {
    window.e = e;
    window.render();
  }, current);
  await page.getByText("CONTEXT_CHANGED:", { exact: false }).waitFor();
  releaseList();
  await delay(150);
  assert.equal(
    await page
      .getByText("What does the original establish?", { exact: true })
      .count(),
    0,
  );
  assert.equal(
    await page.getByRole("button", { name: "Open exact workpaper" }).count(),
    0,
  );
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        "409 retains authored question",
        "ambiguous transport retries exact command",
        "historical workpaper v1 preview",
        "recipient accept and explicit completion response",
        "changed scope redacts links; no formal commands",
      ],
    }),
  );
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
