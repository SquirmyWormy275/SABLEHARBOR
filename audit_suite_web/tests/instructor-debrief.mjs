import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { createHash } from "node:crypto";
import assert from "node:assert/strict";
const base = "http://127.0.0.1:8846",
  server = spawn(
    process.execPath,
    [
      "node_modules/vite/bin/vite.js",
      "--host",
      "127.0.0.1",
      "--port",
      "8846",
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
  const page = await browser.newPage({ acceptDownloads: true }),
    errors = [],
    calls = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const pin = "a".repeat(64),
    key = "b".repeat(64),
    e = {
      id: "E",
      revision: 3,
      scope: { boundaries: ["B"] },
      permissions: ["instruct"],
      company_source_binding: { branch: "B" },
      artifacts: [
        {
          id: "A",
          name: "Selected original",
          sha256: pin,
          status: "AVAILABLE",
        },
      ],
      tasks: [],
    };
  const options = {
    engagement_id: "E",
    revision: 3,
    key_manifest_sha256: key,
    recipients: [{ id: "L", name: "Learner" }],
    issues: [
      { id: "I", title: "Selected issue" },
      { id: "UNSELECTED", title: "Do not release" },
    ],
    expectations: [{ id: "X", title: "Selected procedure", issue_ids: ["I"] }],
    artifacts: [
      { id: "A", title: "Selected original", sha256: pin, bytes: 15 },
    ],
  };
  let doc,
    confirmLost = true,
    exportLost = true,
    hold = false,
    releaseHold,
    previewNumber = 0;
  const zip = Buffer.from("bounded fixture portable bytes"),
    zipsha = createHash("sha256").update(zip).digest("hex");
  await page.route("**/__debrief", (r) =>
    r.fulfill({
      contentType: "text/html",
      body: `<div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;const rm=await import('/node_modules/.vite/deps/react.js');const React=rm.default??rm;const cm=await import('/node_modules/.vite/deps/react-dom_client.js');const root=(cm.createRoot??cm.default.createRoot)(document.getElementById('root'));const {InstructorDebrief}=await import('/src/InstructorDebrief.tsx');const {InstructorAssistance}=await import('/src/InstructorAssistance.tsx');window.e=${JSON.stringify(e)};window.mode='instructor';window.render=()=>root.render(React.createElement(React.StrictMode,null,window.mode==='instructor'?React.createElement(InstructorDebrief,{engagement:window.e,viewerId:'T',supported:true}):React.createElement(InstructorAssistance,{engagement:window.e,viewerId:'L',supported:true,mode:'learner'})));window.render();</script>`,
    }),
  );
  await page.route("**/api/**", async (route) => {
    const req = route.request(),
      path = new URL(req.url()).pathname,
      body = req.postDataJSON();
    calls.push({ path, method: req.method(), body });
    let value;
    if (path.endsWith("/debrief-options")) value = options;
    else if (path.endsWith("/debrief-preview")) {
      doc = {
        schema: "SELECTED_INSTRUCTOR_DEBRIEF_V1",
        source_references: [
          {
            artifact_id: "A",
            artifact_sha256: pin,
            status: "UNRECORDED",
            native: null,
          },
        ],
        title: body.title,
        version: 1,
        predecessor: null,
        key_manifest_sha256: key,
        learner: {
          actor_id: body.recipient_id,
          revision: body.learner_revision,
          state_sha256: pin,
          event_sha256: pin,
          history_sha256: pin,
          qualification:
            "SHARED_ENGAGEMENT_STATE_NOT_SUBMISSION_OR_INDIVIDUAL_PERFORMANCE",
        },
        sections: body.sections.map((s) => ({
          issues: s.issue_ids.map((id) => ({
            id,
            control_ids: ["C"],
            claim: "Only explicitly chosen authored claim",
            uncertainty: "Unvalidated",
          })),
          expectations: s.expectation_ids.map((id) => ({
            id,
            issue_ids: ["I"],
            procedure: "Review exact support",
            acceptable_alternatives: ["Reasoned alternative"],
          })),
          explanation: s.explanation,
          limitations: s.limitations,
          prompts: s.prompts,
          annotations: s.annotations,
        })),
        qualification:
          "INSTRUCTOR_AUTHORED_UNVALIDATED_LOCATORS_NOT_VERIFIED_NO_GRADING",
      };
      value = {
        preview: {
          id: "P" + ++previewNumber,
          engagement_id: "E",
          instructor_id: "T",
          recipient_id: "L",
          revision: 3,
          key_manifest_sha256: key,
          expires_at: new Date(Date.now() + 60000).toISOString(),
          content: {
            stage: "EXPLANATION",
            text: body.title,
            pointers: [],
            document: doc,
          },
        },
        preview_sha256: pin,
        delivered: false,
      };
      if (hold) {
        hold = false;
        await new Promise((resolve) => (releaseHold = resolve));
      }
    } else if (path.endsWith("/instructor-releases")) {
      value = {
        release_id: "R",
        release_sha256: pin,
        status: "RELEASED",
        delivered: false,
      };
      if (confirmLost) {
        confirmLost = false;
        return route.abort("failed");
      }
    } else if (path.endsWith("/export-preview"))
      value = {
        preview: {
          id: "XP",
          actor_id: await page.evaluate(() =>
            window.mode === "instructor" ? "T" : "L",
          ),
          engagement_id: "E",
          release_id: "R",
          release_sha256: pin,
          filename: "selected-debrief.zip",
          sha256: zipsha,
          bytes: zip.length,
          members: [
            { name: "debrief.html", bytes: 15, sha256: pin },
            { name: "manifest.json", bytes: 20, sha256: pin },
          ],
          expires_at: new Date(Date.now() + 60000).toISOString(),
        },
        preview_sha256: pin,
        exported: false,
      };
    else if (path.endsWith("/export")) {
      if (exportLost) {
        exportLost = false;
        return route.abort("failed");
      }
      return route.fulfill({
        contentType: "application/zip",
        headers: { "X-Content-SHA256": zipsha },
        body: zip,
      });
    } else if (path.endsWith("/assistance"))
      value = [
        {
          release_id: "R",
          status: "RELEASED",
          delivered: false,
          acknowledged: false,
        },
      ];
    else if (path.endsWith("/assistance/R"))
      value = {
        release_id: "R",
        release_sha256: pin,
        content: {
          stage: "EXPLANATION",
          text: "Selected debrief",
          pointers: [],
          document: doc,
        },
        pre_release_revision: 3,
        understanding: "NOT_INFERRED",
      };
    else throw Error("Unexpected route " + path);
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(value),
    });
  });
  await page.goto(base + "/__debrief");
  await page
    .getByText("Prepare a selected explanation debrief", { exact: true })
    .click();
  assert.equal(calls.length, 0);
  await page.getByRole("button", { name: "Load debrief choices" }).click();
  await page.getByLabel("Debrief recipient", { exact: true }).selectOption("L");
  await page
    .getByLabel("Debrief title", { exact: true })
    .fill("Selected debrief");
  await page.getByLabel("Learner history revision", { exact: true }).fill("1");
  await page
    .getByLabel("Section 1 issues", { exact: true })
    .selectOption(["I"]);
  await page
    .getByLabel("Section 1 expectations", { exact: true })
    .selectOption(["X"]);
  await page
    .getByLabel("Section 1 explanation", { exact: true })
    .fill("Authored bounded explanation");
  await page
    .getByLabel("Section 1 limitations", { exact: true })
    .fill("No independent professional validation");
  await page
    .getByLabel("Section 1 prompt 1", { exact: true })
    .fill("What supports the interpretation?");
  await page
    .getByLabel("Annotate original in section 1", { exact: true })
    .selectOption("A");
  await page
    .getByLabel("Annotation 1.1", { exact: true })
    .fill("Exact selected original");
  await page
    .getByRole("button", { name: "Preview selected debrief", exact: true })
    .click();
  const preview = page.getByRole("region", {
    name: "Exact debrief release preview",
  });
  await preview.waitFor();
  assert(!(await preview.textContent()).includes("UNSELECTED"));
  assert.equal(
    calls.filter((c) => c.path.endsWith("/instructor-releases")).length,
    0,
  );
  await page
    .getByRole("button", { name: "Confirm selected debrief release" })
    .click();
  await page
    .getByRole("button", { name: "Retry exact debrief confirmation" })
    .click();
  await page
    .getByText("Selected explanation released to the named learner.", {
      exact: false,
    })
    .waitFor();
  const confirms = calls.filter((c) => c.path.endsWith("/instructor-releases"));
  assert.deepEqual(confirms[0].body, confirms[1].body);
  let downloads = 0;
  page.on("download", () => downloads++);
  await page.getByRole("button", { name: "Preview portable export" }).click();
  await page.getByRole("heading", { name: "Files in this export" }).waitFor();
  assert.equal(downloads, 0);
  await page
    .getByRole("button", { name: "Confirm and download this export" })
    .click();
  const retry = page.getByRole("button", {
    name: "Retry exact export request",
  });
  await retry.waitFor();
  const download = page.waitForEvent("download");
  await retry.click();
  await download;
  const exports = calls.filter((c) => c.path.endsWith("/export"));
  assert.deepEqual(exports[0].body, exports[1].body);
  assert.equal(downloads, 1);
  // A late preview must disappear after authority/revision changes.
  hold = true;
  await page
    .getByRole("button", { name: "Preview selected debrief", exact: true })
    .click();
  while (!releaseHold) await delay(10);
  await page.evaluate(() => {
    window.e = { ...window.e, revision: 4 };
    window.render();
  });
  releaseHold();
  await delay(100);
  assert.equal(
    await page
      .getByRole("region", { name: "Exact debrief release preview" })
      .count(),
    0,
  );
  // Learner integration loads only selected confirmed document, never instructor options.
  const before = calls.length;
  await page.evaluate(() => {
    window.mode = "learner";
    window.e = { ...window.e, permissions: ["learn"] };
    window.render();
  });
  await page
    .getByRole("button", { name: "Open assistance R", exact: true })
    .click();
  await page
    .getByRole("article", { name: "Selected debrief document" })
    .waitFor();
  assert(!(await page.locator("body").textContent()).includes("UNSELECTED"));
  assert(
    !calls.slice(before).some((c) => c.path.includes("/instructor-releases")),
  );
  assert.equal(downloads, 1);
  await page.evaluate(() => {
    window.e = { ...window.e, permissions: [] };
    window.render();
  });
  await delay(50);
  assert.equal(
    await page
      .getByRole("article", { name: "Selected debrief document" })
      .count(),
    0,
  );
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        "explicit structured selection/full preview",
        "exact lost-confirmation retry",
        "export names/bytes preview without download",
        "exact lost-export retry and SHA-verified download",
        "late preview discarded on revision change",
        "learner confirmed-only renderer and no Key options",
        "permission loss clears content",
      ],
    }),
  );
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
