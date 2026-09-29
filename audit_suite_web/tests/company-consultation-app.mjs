// Full-App synthetic HTTP fixture; no local company data, model or formal audit mutation.
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import assert from "node:assert/strict";
const port = 8843,
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
  const q = { meeting_id: "M1", message_id: "Q1", sha256: "a".repeat(64) },
    r = { meeting_id: "M1", message_id: "R1", sha256: "b".repeat(64) };
  const consultation = {
    kind: "CORRECTION_REQUEST",
    question_ref: q,
    response_ref: r,
  };
  const completed = [];
  for (const durable of [false, true]) {
    const page = await browser.newPage({
        viewport: { width: 1440, height: 1100 },
      }),
      errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const e = {
      id: "E-CONSULT",
      title: "Neutral exact consultation workroom",
      revision: 1,
      discipline: "IT",
      mode: "CLEAN",
      phase: "ACTIVE",
      permissions: ["learn"],
      simulated_at: "2027-02-02T09:00:00Z",
      scope: {
        programs: ["SOC2"],
        period_start: "2027-02-01",
        period_end: "2027-02-01",
        report_type: "Type 2",
        boundaries: ["corporate"],
      },
      company_source_binding: { company: "LOCAL", branch: "one" },
      evidence_acquisition: "COMPANY_SOURCE_COLLECTION",
      capabilities: { company_consultations: true, background_jobs: durable },
      people: [
        { id: "P1", name: "First contact", title: "Local owner" },
        { id: "P2", name: "Second contact", title: "Local reviewer" },
      ],
      meetings: [
        {
          id: "M1",
          title: "Original contact meeting",
          person_id: "P1",
          status: "OPEN",
          messages: [
            {
              id: "Q1",
              role: "user",
              content: "Which date does the original establish?",
            },
            {
              id: "R1",
              role: "assistant",
              claim_type: "PERSONA_STATEMENT",
              content: "The original does not establish a completion date.",
              person_id: "P1",
            },
          ],
        },
        {
          id: "M2",
          title: "Other contact meeting",
          person_id: "P2",
          status: "OPEN",
          messages: [
            {
              id: "PRIOR-CONSULT",
              role: "assistant",
              claim_type: "PERSONA_STATEMENT",
              content: "A later statement does not replace the original.",
              consultation: {
                ...consultation,
                relation: "CANNOT_ESTABLISH",
                source_support: "SUPPORT_NOT_SUPPLIED",
              },
            },
          ],
        },
      ],
      company_consultation_inputs: {
        status: "AVAILABLE",
        questions: [
          {
            ref: q,
            person_id: "P1",
            meeting_title: "Original contact meeting",
            content: "Which date does the original establish?",
            responses: [
              {
                ref: r,
                person_id: "P1",
                content: "The original does not establish a completion date.",
              },
            ],
          },
        ],
      },
    };
    for (const key of [
      "controls",
      "tasks",
      "requests",
      "artifacts",
      "populations",
      "selections",
      "calendar",
      "findings",
      "workpapers",
      "reviews",
      "surveys",
      "events",
      "notes",
      "exports",
    ])
      e[key] = [];
    const commands = [],
      jobs = [],
      requests = [];
    let lose = durable,
      finish = false;
    const job = {
      id: "JOB-CONSULT",
      kind: "meeting.message",
      status: "RUNNING",
      job_revision: 2,
      expected_revision: 1,
      attempts: 1,
      created_at: "2027-02-02",
      updated_at: "2027-02-02",
      result_revision: null,
      error_code: null,
      error_message: null,
    };
    await page.route("**/api/**", async (route) => {
      const req = route.request(),
        path = new URL(req.url()).pathname;
      requests.push([req.method(), path]);
      const reply = (value) =>
        route.fulfill({
          contentType: "application/json",
          body: JSON.stringify(value),
        });
      if (path === "/api/bootstrap")
        return reply({
          viewer: {
            id: "AUDITOR",
            display_name: "Technical fixture",
            roles: ["learner"],
          },
          csrf_token: "fixture",
          engagements: [e],
          capabilities: e.capabilities,
          background_command_kinds: durable ? ["meeting.message"] : [],
          programs: [{ id: "SOC2", name: "SOC 2" }],
          people: [],
          controls: [],
        });
      if (path === "/api/engagements/" + e.id) return reply(e);
      if (path.endsWith("/commands")) {
        const c = req.postDataJSON();
        assert.equal(c.kind, "meeting.message");
        commands.push(c);
        e.revision++;
        return reply(e);
      }
      if (path.endsWith("/jobs")) {
        if (req.method() === "POST") {
          const c = req.postDataJSON();
          assert.equal(c.kind, "meeting.message");
          jobs.push(c);
          if (lose) {
            lose = false;
            return route.abort("failed");
          }
          return reply(job);
        }
        return reply({
          jobs: finish
            ? [{ ...job, status: "COMPLETED", result_revision: e.revision }]
            : [],
        });
      }
      throw Error("Unexpected API " + req.method() + " " + path);
    });
    await page.goto(base + "/?engagement=" + e.id + "&view=meetings");
    await page.getByRole("button", { name: /Other contact meeting/ }).click();
    async function pick() {
      const summary = page.getByText(
        "Refer an earlier question or request a correction",
        { exact: true },
      );
      if (!(await page.getByLabel("Consultation request type").isVisible()))
        await summary.click();
      await page
        .getByLabel("Consultation request type")
        .selectOption("CORRECTION_REQUEST");
      await page
        .getByLabel("Earlier consultation question")
        .selectOption("M1:Q1");
      await page.getByLabel("Earlier consultation response").selectOption("R1");
      await page
        .getByRole("button", { name: "Use exact consultation references" })
        .click();
    }
    await page
      .getByText("Company statement about an earlier exchange", { exact: true })
      .click();
    await page.getByRole("button", { name: "Open exact reply" }).click();
    const exact = page.getByRole("region", {
      name: "Exact referenced conversation message",
    });
    await exact.waitFor();
    assert.match(await exact.innerText(), /R1/);
    assert.match(
      await exact.innerText(),
      /original does not establish a completion date/,
    );
    assert.match(await exact.innerText(), new RegExp(r.sha256));
    await page
      .getByRole("button", { name: "Close dialog", exact: true })
      .click();
    await pick();
    await page
      .getByLabel("Ask the owner")
      .fill("Please clarify the exact earlier reply.");
    await page
      .getByRole("button", { name: "Send message", exact: true })
      .click();
    if (!durable) {
      for (let i = 0; i < 100 && !commands.length; i++) await delay(20);
      assert.deepEqual(commands[0].payload.consultation, consultation);
      await page.waitForFunction(
        () =>
          document.querySelector('[aria-label="Ask the owner"]').value === "",
      );
    } else {
      await page
        .getByRole("alert")
        .filter({ hasText: "question is retained" })
        .waitFor();
      assert.deepEqual(jobs[0].payload.consultation, consultation);
      await page
        .getByRole("button", { name: /Original contact meeting/ })
        .click();
      await page.getByRole("button", { name: /Other contact meeting/ }).click();
      assert.equal(
        await page
          .getByRole("button", { name: "Remove consultation reference" })
          .count(),
        0,
      );
      await page
        .getByRole("button", { name: "Send message", exact: true })
        .click();
      await page
        .getByRole("alert")
        .filter({ hasText: "unconfirmed outcome" })
        .waitFor();
      assert.equal(jobs.length, 1);
      await page
        .getByRole("button", { name: "Restore unconfirmed question" })
        .click();
      await page
        .getByRole("button", { name: "Send message", exact: true })
        .click();
      for (let i = 0; i < 100 && jobs.length < 2; i++) await delay(20);
      assert.deepEqual(jobs[0], jobs[1]);
      await page.waitForFunction(
        () =>
          document.querySelector('[aria-label="Ask the owner"]').value === "",
      );
      await pick();
      await page.getByLabel("Ask the owner").fill("Keep this next question.");
      e.company_source_binding = { company: "LOCAL", branch: "two" };
      e.revision++;
      finish = true;
      for (let i = 0; i < 100; i++) {
        if (
          (await page
            .getByRole("button", { name: "Remove consultation reference" })
            .count()) === 0
        )
          break;
        await delay(100);
      }
      assert.equal(
        await page
          .getByRole("button", { name: "Remove consultation reference" })
          .count(),
        0,
      );
    }
    assert.deepEqual(errors, []);
    assert(
      requests.every(
        ([method, path]) =>
          method === "GET" || path.endsWith(durable ? "/jobs" : "/commands"),
      ),
    );
    completed.push(
      durable
        ? "Durable exact envelope/retry, target+authority clear"
        : "Sync exact consultation payload",
    );
    await page.close();
  }
  console.log(
    JSON.stringify({
      status: "PASS",
      checks: [
        ...completed,
        "Full-App exact original message preview",
        "All HTTP mocked; no model or real audit mutation",
      ],
    }),
  );
} finally {
  await browser?.close();
  server.kill("SIGTERM");
}
