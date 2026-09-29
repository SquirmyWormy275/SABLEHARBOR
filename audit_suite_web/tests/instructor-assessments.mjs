import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";
const base = "http://127.0.0.1:8848",
  server = spawn(
    process.execPath,
    [
      "node_modules/vite/bin/vite.js",
      "--host",
      "127.0.0.1",
      "--port",
      "8848",
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
    },
    history = {
      revision: 1,
      state_sha256: pin,
      history_sha256: pin,
      event_sha256: pin,
    },
    bound = {
      binding: { manifest_sha256: pin, bound_revision: 0 },
      snapshot: { audited_actor_id: "L" },
    };
  const options = {
    engagement_id: "E",
    current_engagement_revision: 3,
    learner_revision: 1,
    key_pin: pin,
    rubric_sha256: pin,
    inventory_sha256: pin,
    selected_state_sha256: pin,
    selected_history_sha256: pin,
    selected_history_tip_sha256: pin,
    audited_actor_id: "L",
    bound_revision: 0,
    issues: [
      {
        id: "I",
        claim: "Authored interpretation",
        control_ids: ["C"],
        uncertainty: "Unvalidated",
      },
    ],
    expectations: [
      {
        id: "X",
        issue_ids: ["I"],
        procedure: "Authored expected procedure",
        acceptable_alternatives: ["Defensible alternate support"],
      },
    ],
    references: [
      {
        id: "REF",
        kind: "workpaper",
        record_id: "W",
        version: 1,
        inventory_sha256: pin,
        content_sha256: pin,
        relation: "EXACT_RECORDED_WORKPAPER_VERSION",
        expectation_ids: ["X"],
      },
    ],
  };
  let records = [],
    lost = true,
    conflict = false,
    hold = false,
    releaseHold,
    redact = false;
  const receipts = new Map();
  await page.route("**/__assessments", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;const rm=await import('/node_modules/.vite/deps/react.js');const React=rm.default??rm;const cm=await import('/node_modules/.vite/deps/react-dom_client.js');const root=(cm.createRoot??cm.default.createRoot)(document.getElementById('root'));const {InstructorAssessments}=await import('/src/InstructorAssessments.tsx');const {InstructorComparison}=await import('/src/InstructorComparison.tsx');window.e=${JSON.stringify(e)};window.historyPin=${JSON.stringify(history)};window.bound=${JSON.stringify(bound)};window.render=()=>root.render(React.createElement(React.StrictMode,null,window.compare?React.createElement(InstructorComparison,{engagement:window.e,viewerId:'T',assessmentsEnabled:true,bound:window.bound}):React.createElement(InstructorAssessments,{engagement:window.e,viewerId:'T',enabled:true,bound:window.bound,history:window.historyPin})));window.render();</script>`,
    }),
  );
  await page.route("**/api/**", async (route) => {
    const req = route.request(),
      path = new URL(req.url()).pathname,
      body = req.postDataJSON();
    calls.push({ path, method: req.method(), body });
    let value;
    if (path.endsWith("/instructor-comparison")) {
      value = {
        status: "DETERMINISTIC_LINK_INVENTORY_ONLY",
        engagement_id: "E",
        audited_actor_id: "L",
        binding_manifest_sha256: pin,
        bound_revision: 0,
        selected_history_revision: 1,
        current_revision: 3,
        selected_state_sha256: pin,
        selected_history_sha256: pin,
        selected_history_tip_sha256: pin,
        grading: "NOT_PERFORMED",
        professional_validation: "UNVALIDATED",
        mismatches: [],
        limits: [],
        sources: [],
        expectations: [],
        audited_actor_activity: [],
        shared_workspace_activity_count: 0,
      };
    } else if (path.endsWith("/options")) {
      value = structuredClone(options);
      if (hold) {
        hold = false;
        await new Promise((resolve) => (releaseHold = resolve));
      }
    } else if (req.method() === "POST") {
      if (conflict) {
        conflict = false;
        return route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({ error: "Historical basis changed" }),
        });
      }
      if (receipts.has(body.command_id)) value = receipts.get(body.command_id);
      else {
        const {
          command_id,
          expected_engagement_revision,
          learner_revision,
          key_pin,
          rubric_sha256,
          inventory_sha256,
          predecessor,
          ...authored
        } = body;
        const id = "A" + (records.length + 1),
          version = predecessor
            ? records.find((r) => r.id === predecessor.id).version + 1
            : 1;
        const document = {
          schema: "INSTRUCTOR_AUTHORED_ASSESSMENT_V1",
          id,
          version,
          actor_id: "T",
          engagement_id: "E",
          recorded_at: "2026-09-22T12:00:00Z",
          predecessor,
          pins: {
            key_pin,
            rubric_sha256,
            inventory_sha256,
            audited_actor_id: "L",
            learner_revision,
            selected_state_sha256: pin,
            selected_history_sha256: pin,
            selected_history_tip_sha256: pin,
            bound_revision: 0,
          },
          authored,
          selected_issues: options.issues,
          selected_expectations: options.expectations,
          references: options.references,
          qualification:
            "INSTRUCTOR_AUTHORED_UNVALIDATED_NO_AGGREGATE_GRADE_SHARED_STATE_NOT_SUBMISSION",
        };
        value = {
          id,
          engagement_id: "E",
          version,
          sha256: pin,
          predecessor,
          saved_engagement_revision: 3,
          current_engagement_revision: 3,
          learner_revision,
          context_status: "CURRENT",
          personal_content_visible: true,
          correction_allowed: true,
          title: authored.title,
          document,
        };
        records.push(value);
        receipts.set(command_id, value);
      }
      if (lost) {
        lost = false;
        return route.abort("failed");
      }
    } else if (path.endsWith("/instructor-assessments"))
      value = {
        engagement_id: "E",
        current_engagement_revision: 3,
        assessments: records.map(({ document, ...r }) =>
          redact
            ? {
                ...r,
                title: undefined,
                personal_content_visible: false,
                correction_allowed: false,
                context_status: "KEY_CHANGED",
              }
            : r,
        ),
      };
    else value = records.find((r) => path.endsWith("/" + r.id));
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(value),
    });
  });
  await page.goto(base + "/__assessments");
  await page
    .getByText("Instructor assessment of this recorded work", { exact: true })
    .click();
  assert.equal(calls.length, 0);
  await page
    .getByRole("button", { name: "Load exact assessment choices" })
    .click();
  await page
    .getByLabel("Assessment title", { exact: true })
    .fill("Explicit instructor judgment");
  await page.getByLabel("Assessment issues", { exact: true }).selectOption("I");
  await page
    .getByLabel("Assessment expectations", { exact: true })
    .selectOption("X");
  for (const d of [
    "discovery",
    "evidence",
    "testing",
    "judgment",
    "documentation",
    "follow-through",
  ]) {
    assert.equal(
      await page.getByLabel(d + " assessment", { exact: true }).inputValue(),
      "",
    );
    await page
      .getByLabel(d + " assessment", { exact: true })
      .fill("Not assessed: " + d);
    await page
      .getByLabel(d + " rationale", { exact: true })
      .fill("Requires independent evaluation of " + d);
  }
  await page
    .getByText("documentation · 0 selected historical references", {
      exact: true,
    })
    .click();
  await page
    .getByRole("checkbox", {
      name: "workpaper W · version 1 · EXACT_RECORDED_WORKPAPER_VERSION",
    })
    .check();
  await page
    .getByRole("button", { name: "Add alternatives", exact: true })
    .click();
  await page
    .getByLabel("alternatives 1 expectation_id", { exact: true })
    .selectOption("X");
  await page
    .getByLabel("alternatives 1 description", { exact: true })
    .fill("A defensible alternative supplied by instructor");
  await page
    .getByLabel("alternatives 1 rationale", { exact: true })
    .fill("Explicit rationale, not automatic acceptance");
  await page
    .getByRole("button", { name: "Add overrides", exact: true })
    .click();
  await page
    .getByLabel("overrides 1 expectation_id", { exact: true })
    .selectOption("X");
  await page
    .getByLabel("overrides 1 prior_interpretation", { exact: true })
    .fill("Earlier authored interpretation");
  await page
    .getByLabel("overrides 1 replacement", { exact: true })
    .fill("Explicit revised interpretation");
  await page
    .getByLabel("overrides 1 rationale", { exact: true })
    .fill("Reasoned instructor override");
  await page.getByRole("button", { name: "Add defects", exact: true }).click();
  await page
    .getByLabel("defects 1 issue_id", { exact: true })
    .selectOption("I");
  await page
    .getByLabel("defects 1 description", { exact: true })
    .fill("Potential scenario ambiguity");
  await page
    .getByLabel("defects 1 impact", { exact: true })
    .fill("Limits supported judgment");
  await page
    .getByLabel("defects 1 rationale", { exact: true })
    .fill("Requires author review");
  await page
    .getByRole("button", { name: "Save instructor assessment", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Retry exact assessment save" })
    .click();
  await page
    .getByRole("region", { name: "Opened instructor assessment" })
    .waitFor();
  const saves = calls.filter((c) => c.method === "POST");
  assert.deepEqual(saves[0].body, saves[1].body);
  assert.equal(saves[0].body.learner_revision, 1);
  assert.equal(saves[0].body.dimensions.length, 6);
  assert.deepEqual(
    saves[0].body.dimensions.find((d) => d.dimension === "documentation")
      .reference_ids,
    ["REF"],
  );
  assert(!("score" in saves[0].body));
  assert.equal(records.length, 1);
  const original = structuredClone(records[0]);
  await page
    .getByRole("button", {
      name: "Prepare correction using history revision 1",
    })
    .click();
  await delay(100);
  assert.deepEqual(errors, []);
  await page
    .getByLabel("documentation assessment", { exact: true })
    .fill("Explicit corrected documentation judgment");
  await page
    .getByRole("button", { name: "Save instructor assessment", exact: true })
    .click();
  await page
    .getByRole("region", { name: "Assessment history" })
    .getByRole("button", { name: "Open assessment A2", exact: true })
    .waitFor();
  assert.deepEqual(records[0], original);
  assert.deepEqual(records[1].predecessor, { id: "A1", sha256: pin });
  assert.equal(records[1].version, 2);
  await page
    .getByRole("button", {
      name: "Prepare correction using history revision 1",
    })
    .click();
  await page
    .getByLabel("Assessment title", { exact: true })
    .fill("Keep text after conflict");
  conflict = true;
  await page
    .getByRole("button", { name: "Save instructor assessment", exact: true })
    .click();
  await page
    .getByRole("alert")
    .filter({ hasText: "Historical basis changed" })
    .waitFor();
  await page
    .getByRole("button", { name: "Load exact assessment choices" })
    .click();
  assert.equal(
    await page.getByLabel("Assessment title", { exact: true }).inputValue(),
    "Keep text after conflict",
  );
  redact = true;
  await page.getByRole("button", { name: "Load assessment history" }).click();
  await page.getByText("KEY_CHANGED", { exact: false }).first().waitFor();
  assert.equal(
    await page
      .getByRole("region", { name: "Opened instructor assessment" })
      .count(),
    0,
  );
  assert.equal(
    await page
      .getByRole("region", { name: "Assessment history" })
      .getByRole("heading", { name: "Explicit instructor judgment" })
      .count(),
    0,
  );
  hold = true;
  await page
    .getByRole("button", { name: "Load exact assessment choices" })
    .click();
  while (!releaseHold) await delay(10);
  await page.evaluate(() => {
    window.e = { ...window.e, revision: 4 };
    window.render();
  });
  releaseHold();
  await delay(100);
  assert.equal(
    await page.getByLabel("Assessment title", { exact: true }).count(),
    0,
  );
  const count = calls.length;
  await page.evaluate(() => {
    window.e = { ...window.e, permissions: ["learn"] };
    window.render();
  });
  await delay(50);
  assert.equal(
    await page
      .getByText("Instructor assessment of this recorded work", { exact: true })
      .count(),
    0,
  );
  assert.equal(calls.length, count);
  await page.evaluate(() => {
    window.compare = true;
    window.e = { ...window.e, revision: 3, permissions: ["instruct"] };
    window.bound = {
      ...window.bound,
      snapshot: { ...window.bound.snapshot, authored: { expectations: [] } },
    };
    window.render();
  });
  await page
    .getByText("Trace recorded work against bound expectations", {
      exact: true,
    })
    .click();
  assert.equal(
    await page
      .getByText("Instructor assessment of this recorded work", { exact: true })
      .count(),
    0,
  );
  await page.getByLabel("History revision", { exact: true }).fill("1");
  await page
    .getByRole("button", { name: "Trace recorded links", exact: true })
    .click();
  await page
    .getByText("Instructor assessment of this recorded work", { exact: true })
    .waitFor();
  await page.getByLabel("History revision", { exact: true }).fill("2");
  assert.equal(
    await page
      .getByText("Instructor assessment of this recorded work", { exact: true })
      .count(),
    0,
  );
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        "no inferred initial judgments/no automatic fetch",
        "six authored dimensions/exact WPv1 reference",
        "explicit alternative/override/defect",
        "lost-save exact retry",
        "immutable explicit correction history",
        "409 draft preservation",
        "stale Key metadata redaction",
        "late selected-context response discarded",
        "learner no endpoints/DOM",
        "comparison mount requires successful explicit revision and clears when changed",
      ],
    }),
  );
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
