import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";
const port = 8842,
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
    api = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const q = { meeting_id: "M1", message_id: "Q", sha256: "a".repeat(64) },
    r = { meeting_id: "M1", message_id: "R", sha256: "b".repeat(64) };
  const state = {
    id: "E",
    revision: 1,
    scope: {},
    permissions: ["learn"],
    people: [{ id: "P2", name: "Second contact", title: "Local reviewer" }],
    meetings: [
      {
        id: "M1",
        person_id: "P1",
        messages: [
          { id: "Q", role: "user", content: "Which exact date is supported?" },
          {
            id: "R",
            role: "assistant",
            content: "The supplied source does not establish a date.",
            claim_type: "PERSONA_STATEMENT",
          },
        ],
      },
      { id: "M2", person_id: "P2", messages: [] },
    ],
    company_consultation_inputs: {
      status: "AVAILABLE",
      questions: [
        {
          ref: q,
          meeting_title: "Earlier meeting",
          person_id: "P1",
          content: "Which exact date is supported?",
          responses: [
            {
              ref: r,
              person_id: "P1",
              content: "The supplied source does not establish a date.",
            },
          ],
        },
      ],
    },
  };
  const message = {
    id: "NEW",
    role: "assistant",
    claim_type: "PERSONA_STATEMENT",
    person_id: "P2",
    consultation: {
      kind: "CORRECTION_REQUEST",
      question_ref: q,
      response_ref: r,
      relation: "CANNOT_ESTABLISH",
      source_support: "SUPPORT_NOT_SUPPLIED",
      source_manifest: [
        {
          source_id: "SRC-1",
          source_identity: {
            company: "LOCAL",
            branch: "exercise",
            system: "training",
            record: "assignment",
            version: 1,
            sha256: "c".repeat(64),
            source_system_alias: "training:register",
          },
          qualifiers: ["LOCAL_EXERCISE"],
          private_path: "/must-not-display",
        },
      ],
    },
  };
  await page.route("**/api/**", (route) => {
    api.push(route.request().url());
    return route.abort();
  });
  await page.route("**/__consultation-test", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<html><body><input aria-label="Question draft" value="Keep my authored question"><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;const rm=await import('/node_modules/.vite/deps/react.js');const React=rm.default??rm;const cm=await import('/node_modules/.vite/deps/react-dom_client.js');const createRoot=cm.createRoot??cm.default.createRoot;const {MeetingConsultation}=await import('/src/MeetingConsultation.tsx');const {ConsultationProvenance}=await import('/src/ConsultationProvenance.tsx');const root=createRoot(document.getElementById('root'));window.e=${JSON.stringify(state)};window.target='M2';window.viewer='A';window.value=null;window.opened=[];window.render=()=>root.render(React.createElement(React.Fragment,null,React.createElement(MeetingConsultation,{engagement:window.e,viewerId:window.viewer,targetMeetingId:window.target,value:window.value,onChange:v=>{window.value=v;window.render()}}),React.createElement(ConsultationProvenance,{engagement:window.e,message:${JSON.stringify(message)},onPreview:(kind,row,reference)=>window.opened.push({kind,id:row.id,reference})})));window.render();</script></body></html>`,
    }),
  );
  await page.goto(base + "/__consultation-test");
  await page
    .getByText("Refer an earlier question or request a correction", {
      exact: true,
    })
    .click();
  await page.getByLabel("Earlier consultation question").selectOption("M1:Q");
  await page
    .getByRole("button", { name: "Use exact consultation references" })
    .click();
  assert.deepEqual(await page.evaluate(() => window.value), {
    kind: "REFERRAL",
    question_ref: q,
    response_ref: null,
  });
  await page
    .getByLabel("Consultation request type")
    .selectOption("CORRECTION_REQUEST");
  await page.getByLabel("Earlier consultation question").selectOption("M1:Q");
  assert.equal(
    await page
      .getByRole("button", { name: "Use exact consultation references" })
      .isDisabled(),
    true,
  );
  await page.getByLabel("Earlier consultation response").selectOption("R");
  await page
    .getByRole("button", { name: "Use exact consultation references" })
    .click();
  assert.deepEqual(await page.evaluate(() => window.value), {
    kind: "CORRECTION_REQUEST",
    question_ref: q,
    response_ref: r,
  });
  await page
    .getByText("Company statement about an earlier exchange", { exact: true })
    .click();
  await page.getByRole("button", { name: "Open exact reply" }).click();
  assert.equal(
    (await page.evaluate(() => window.opened))[0].reference.message_id,
    "R",
  );
  assert.match(
    await page.locator("body").innerText(),
    /attributed statement, not verification/,
  );
  assert.match(
    await page.locator("body").innerText(),
    /Responding contact: Second contact · Local reviewer \(P2\)/,
  );
  await page
    .getByText("Original source context recorded with this statement", {
      exact: true,
    })
    .click();
  assert.match(await page.locator("body").innerText(), /training:register/);
  assert.doesNotMatch(
    await page.locator("body").innerText(),
    /must-not-display/,
  );
  await page.evaluate(() => {
    window.viewer = "B";
    window.render();
  });
  await page.waitForFunction(() => window.value === null);
  await page
    .getByText("Refer an earlier question or request a correction", {
      exact: true,
    })
    .click();
  assert.equal(
    await page.getByLabel("Question draft").inputValue(),
    "Keep my authored question",
  );
  await page.evaluate(() => {
    window.e = {
      ...window.e,
      revision: 2,
      company_consultation_inputs: {
        status: "INPUT_LIMIT_EXCEEDED",
        questions: [],
      },
    };
    window.render();
  });
  await page
    .getByText("Earlier conversation references unavailable:", { exact: false })
    .waitFor();
  assert.equal(
    await page.getByRole("button", { name: "Open exact reply" }).count(),
    0,
  );
  assert.deepEqual(api, []);
  const queued = {
    command_id: "ORIGINAL",
    expected_revision: 1,
    kind: "meeting.message",
    payload: {
      meeting_id: "M2",
      content: "Please clarify the supplied earlier statement.",
      consultation: {
        kind: "CORRECTION_REQUEST",
        question_ref: q,
        response_ref: r,
      },
    },
  };
  const job = {
    id: "JOB",
    kind: "meeting.message",
    status: "FAILED",
    job_revision: 2,
    expected_revision: 1,
    attempts: 1,
    error_code: "INFERENCE_TIMEOUT",
    error_message: "Timed out",
  };
  const inspectedRequests = [];
  await page.route("**/api/**", (route) => {
    const request = route.request();
    inspectedRequests.push({
      method: request.method(),
      path: new URL(request.url()).pathname,
    });
    assert.equal(request.method(), "GET");
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(
        request.url().endsWith("/input") ? queued : { jobs: [job] },
      ),
    });
  });
  await page.route("**/__queued-consultation", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<html><body><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;const rm=await import('/node_modules/.vite/deps/react.js');const React=rm.default??rm;const cm=await import('/node_modules/.vite/deps/react-dom_client.js');const createRoot=cm.createRoot??cm.default.createRoot;const {BackgroundWork}=await import('/src/BackgroundWork.tsx');createRoot(document.getElementById('root')).render(React.createElement(BackgroundWork,{engagement:${JSON.stringify(state)},viewerId:'A',onInspect:()=>{},onCompleted:()=>{}}));</script></body></html>`,
    }),
  );
  await page.goto(base + "/__queued-consultation");
  const retry = page.getByRole("button", { name: "Retry original command" });
  await retry.waitFor();
  assert.equal(await retry.isDisabled(), true);
  await page.getByRole("button", { name: "Inspect queued question" }).click();
  await page
    .getByText("Original learner-requested consultation: CORRECTION_REQUEST", {
      exact: true,
    })
    .waitFor();
  const text = await page.locator("body").innerText();
  assert(text.includes(q.sha256) && text.includes(r.sha256));
  assert.match(
    text,
    /No original source records were selected for this consultation/,
  );
  assert.doesNotMatch(text, /automatic bounded source sampling/);
  assert(inspectedRequests.some((r) => r.path.endsWith("/JOB/input")));
  assert(inspectedRequests.every((r) => r.method === "GET"));
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        "explicit referral exact question pin",
        "correction requires exact response",
        "attributed statement + original source metadata",
        "viewer change clears selection without question draft",
        "unavailable projection blocks historical navigation",
        "picker makes no API/model calls; queued inspector reads exact original input only",
      ],
    }),
  );
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
