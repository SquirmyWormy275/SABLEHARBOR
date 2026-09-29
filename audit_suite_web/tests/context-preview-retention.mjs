// Full-App regression for the context loss observed against the real local backend.
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";
const base = "http://127.0.0.1:8850",
  server = spawn(
    process.execPath,
    [
      "node_modules/vite/bin/vite.js",
      "--host",
      "127.0.0.1",
      "--port",
      "8850",
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
    posts = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const e = {
    id: "E",
    title: "Context preview fixture",
    revision: 1,
    phase: "ACTIVE",
    discipline: "IT",
    mode: "CLEAN",
    permissions: ["learn"],
    simulated_at: "2027-01-01T00:00:00Z",
    scope: {
      programs: [],
      boundaries: ["corporate"],
      period_start: "2027-01-01",
      period_end: "2027-12-31",
    },
    capabilities: { personal_views: true, investigation_handoffs: true },
  };
  for (const k of [
    "controls",
    "people",
    "tasks",
    "requests",
    "artifacts",
    "meetings",
    "notes",
    "populations",
    "selections",
    "calendar",
    "findings",
    "workpapers",
    "reviews",
    "surveys",
    "events",
    "exports",
  ])
    e[k] = [];
  e.workpapers = [
    {
      id: "W",
      title: "Original workpaper",
      versions: [
        { version: 1, text: "Earlier exact work" },
        { version: 2, text: "Later work" },
      ],
    },
  ];
  const handoff = {
    id: "H",
    version: 2,
    status: "ACCEPTED",
    engagement_id: "E",
    current_engagement_revision: 1,
    sender_id: "OTHER",
    recipient_id: "L",
    acting_role: "RECIPIENT",
    shared_content_visible: true,
    context_status: "CURRENT",
    allowed_actions: ["COMPLETE"],
    content: {
      title: "Inspect prior work",
      question: "What does v1 support?",
      next_step: "Inspect exact original.",
      links: [
        { kind: "workpaper", id: "W", version: 1, sha256: "a".repeat(64) },
      ],
      response: "",
      response_author_id: null,
    },
  };
  await page.route("**/api/**", (r) => {
    const req = r.request(),
      p = new URL(req.url()).pathname;
    if (req.method() !== "GET") {
      posts.push(p);
      return r.fulfill({ status: 400, json: { error: "Unexpected mutation" } });
    }
    let value;
    if (p === "/api/bootstrap")
      value = {
        viewer: { id: "L", display_name: "Learner", roles: ["learner"] },
        csrf_token: "test",
        engagements: [e],
        capabilities: e.capabilities,
        programs: [],
        people: [],
        controls: [],
      };
    else if (p === "/api/engagements/E") value = e;
    else if (p.endsWith("/members"))
      value = {
        engagement_id: "E",
        engagement_revision: 1,
        members: [{ id: "OTHER", display_name: "Other", permission: "learn" }],
      };
    else if (p.endsWith("/handoffs")) value = { handoffs: [handoff] };
    else if (p.endsWith("/saved-views")) value = { views: [] };
    else throw Error("Unexpected path " + p);
    return r.fulfill({ json: value });
  });
  await page.goto(base + "/?engagement=E&view=review");
  await page.getByText("Share an investigation", { exact: true }).click();
  await page
    .getByLabel("Response for H", { exact: true })
    .fill("Unsaved response must survive original inspection");
  await page.getByText("Personal saved views", { exact: true }).click();
  await page
    .getByLabel("View title", { exact: true })
    .fill("Unsaved view title");
  const opener = page.getByRole("button", {
    name: "Open exact workpaper",
    exact: true,
  });
  await opener.click();
  await page
    .getByRole("dialog")
    .getByText(
      "Showing explicitly linked workpaper version 1. Other versions are not substituted.",
      { exact: true },
    )
    .waitFor();
  assert.equal(
    await page.locator("[data-retained-contexts]").getAttribute("hidden"),
    "",
  );
  assert.equal(
    await page.locator("[data-retained-contexts]").getAttribute("inert"),
    "",
  );
  await page.keyboard.press("Escape");
  await page.getByRole("dialog").waitFor({ state: "hidden" });
  await page.waitForFunction(
    () => document.activeElement?.textContent === "Open exact workpaper",
  );
  assert.equal(
    await page.getByLabel("Response for H", { exact: true }).inputValue(),
    "Unsaved response must survive original inspection",
  );
  assert.equal(
    await page.getByLabel("View title", { exact: true }).inputValue(),
    "Unsaved view title",
  );
  assert.ok(
    await page.getByLabel("Response for H", { exact: true }).isVisible(),
  );
  assert.deepEqual(posts, []);
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        "main personal panels retained hidden and inert while modal open",
        "unsaved handoff response and saved-view title preserved",
        "exact WPv1 shown",
        "Escape restores exact opener focus",
        "no mutation",
      ],
    }),
  );
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
