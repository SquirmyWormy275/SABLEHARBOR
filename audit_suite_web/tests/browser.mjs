// Public synthetic layout fixture: no hidden scenario truth or production data.
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const output = resolve("../enterprise/generated/audit-suite/build/visuals");
await mkdir(output, { recursive: true });
const server = spawn(
  process.execPath,
  ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5193"],
  { stdio: "ignore" },
);
let browser;
try {
  for (let i = 0; i < 50; i++) {
    try {
      await fetch("http://127.0.0.1:5193");
      break;
    } catch {
      await new Promise((r) => setTimeout(r, 100));
    }
  }
  browser = await chromium.launch({
    executablePath: "/usr/bin/chromium",
    headless: true,
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1050 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const e = {
    id: "ENG-LAYOUT",
    title: "Corporate shared controls · reference assessment",
    revision: 4,
    discipline: "IT",
    mode: "MESSY",
    phase: "ACTIVE",
    simulated_at: "2027-02-12T09:00:00Z",
    scope: {
      programs: ["SOC2", "HIPAA"],
      period_start: "2027-01-01",
      period_end: "2027-12-31",
      report_type: "Type 2",
      boundaries: [
        "Corporate shared services",
        "Reno primary",
        "Boise recovery",
      ],
    },
    capabilities: {
      work_status: true,
      custom_authoring: false,
      experimental_review: false,
      voice: false,
    },
    controls: Array.from({ length: 32 }, (_, i) => ({
      id: `CC-${i + 1}`,
      title: `Access authorization and quarterly review ${i + 1}`,
      framework: "SOC2",
      owner_id: "P-01",
      status: "IN_PROGRESS",
    })),
    people: [
      {
        id: "P-01",
        name: "Morgan Ellis",
        role: "Infrastructure control owner",
        department: "Operations",
      },
    ],
    tasks: [
      {
        id: "T-01",
        title: "Inspect evidence of reviewer approval",
        status: "IN_PROGRESS",
        conclusion: "OPEN",
        control_id: "CC-1",
        owner_id: "P-01",
      },
    ],
    requests: [
      {
        id: "PBC-01",
        title: "Quarterly access review population",
        status: "IN_PROGRESS",
        owner_id: "P-01",
        due_at: "2027-02-15",
      },
    ],
    artifacts: [
      {
        id: "A-01",
        filename: "access-review-population.csv",
        sha256: "a".repeat(64),
        kind: "POPULATION",
        created_at: "2027-02-12",
        request_id: "PBC-01",
      },
    ],
    meetings: [
      {
        id: "M-01",
        title: "Infrastructure walkthrough",
        status: "OPEN",
        participant_ids: ["P-01"],
        messages: [
          {
            id: "MSG-01",
            speaker_name: "Morgan Ellis",
            role: "company",
            claim_type: "statement",
            content:
              "We can walk through the quarterly approval process. Which period and population would you like to inspect?",
          },
        ],
      },
    ],
    notes: [
      {
        id: "N-01",
        title: "Infrastructure walkthrough",
        text: "Confirm population completeness before sample selection.",
        source_message_ids: ["MSG-01"],
      },
    ],
    populations: [
      {
        id: "POP-01",
        title: "Access review population",
        row_count: 120,
        control_id: "CC-1",
        status: "AVAILABLE",
      },
    ],
    selections: [],
    calendar: [
      {
        id: "CAL-01",
        title: "Evidence follow-up",
        scheduled_at: "2027-02-15T10:00:00Z",
        status: "SCHEDULED",
      },
    ],
    findings: [
      {
        id: "F-01",
        title: "Reviewer sign-off requires follow-up",
        status: "OPEN",
        control_id: "CC-1",
        severity: "LOW",
      },
    ],
    workpapers: [
      {
        id: "W-01",
        title: "Access review test",
        status: "DRAFT",
        conclusion: "OPEN",
      },
    ],
    permissions: ["instruct", "review", "learn"],
    reviews: [],
    surveys: [],
    events: [],
  };
  const keyEntry = {
    id: "MM-01.01.V01",
    raw_sha256: "a".repeat(64),
    canonical_sha256: "b".repeat(64),
    key_sha256: "c".repeat(64),
    review: {
      professional: "UNVALIDATED",
      causal_validation: "NOT_RUN",
      grading: "NOT_RUN",
      gaps: ["NEUTRAL_REFERENCE_REVIEW_REQUIRED"],
    },
  };
  const keyContext = {
    status: "UNBOUND_REFERENCE_LIBRARY",
    binding: { status: "NOT_BOUND", engagement_id: e.id },
    archive: { sha256: "d".repeat(64) },
  };
  const keyIndex = {
    ...keyContext,
    audience: "INSTRUCTOR_ONLY",
    required: 1,
    migrated: 1,
    entries: [keyEntry],
  };
  const keyDetail = {
    ...keyContext,
    key: {
      schema: "PRIVATE_INSTRUCTOR_KEY_V1",
      audience: "INSTRUCTOR_ONLY",
      id: keyEntry.id,
      source: {
        raw_sha256: keyEntry.raw_sha256,
        canonical_sha256: keyEntry.canonical_sha256,
        schema_version: "1.0",
      },
      review: keyEntry.review,
      explanation: {
        title: "Neutral instructor browser fixture",
        mechanism: { cause: "Synthetic reference preservation" },
        facts: [{ id: "F1", statement: "Neutral archived fact" }],
        actor_knowledge: [
          { role_ref: "Neutral owner", beliefs: ["Authored statement only"] },
        ],
        artifacts: [{ id: "A1", name: "neutral.txt" }],
        events: [{ id: "E1", trigger: "REQUEST" }],
        playable_paths: [
          { id: "P1", rationale: "Alternative neutral procedure" },
        ],
        rubric: {
          supported_conclusions: ["Bounded neutral observation"],
          acceptable_alternatives: ["Further neutral inquiry"],
          unsupported_guesses: ["Automatic approval"],
        },
      },
      graph: {
        nodes: [{ id: "fact:F1" }],
        edges: [],
        edge_semantics: "AUTHORED_REFERENCES_ONLY_NOT_CORROBORATION",
      },
    },
  };
  let instructorRequests = 0;
  const backgroundJob = {id:'JOB-NEUTRAL',status:'RUNNING',job_revision:2,expected_revision:4,attempts:1,created_at:'2027-02-12T09:00:00Z',updated_at:'2027-02-12T09:00:00Z',result_revision:null,error_code:null,error_message:null};
  let inputReads=0, exactRetries=0;
  let savedContexts=[]; let contextConflict=false;
  let failNextDraftSave = false;
  const personalDrafts = new Map();
  let conflictNextPersonalDraft = false;
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.includes("/drafts/")) {
      let saved = personalDrafts.get(path) ?? {
        status: "EMPTY",
        version: 0,
        fields: {},
        base_workpaper_version: null,
      };
      const method = route.request().method();
      if (method !== "GET") {
        const body = route.request().postDataJSON();
        if (conflictNextPersonalDraft && method === "PUT") {
          conflictNextPersonalDraft = false;
          saved = {
            ...saved,
            status: "DRAFT",
            version: saved.version + 1,
            fields: {
              title: "Other session draft",
              text: "Other session text",
            },
          };
          personalDrafts.set(path, saved);
        }
        if (body.expected_version !== saved.version)
          return route.fulfill({
            status: 409,
            contentType: "application/json",
            body: JSON.stringify({ error: "Concurrent personal draft change" }),
          });
        saved =
          method === "DELETE"
            ? {
                status: "EMPTY",
                version: saved.version + 1,
                fields: {},
                base_workpaper_version: null,
              }
            : {
                status: "DRAFT",
                version: saved.version + 1,
                fields: body.fields,
                base_workpaper_version: body.base_workpaper_version,
              };
        personalDrafts.set(path, saved);
      }
      const current = e.workpapers[0].versions?.at(-1)?.version ?? 1;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...saved,
          workpaper_stale:
            saved.base_workpaper_version != null &&
            saved.base_workpaper_version !== current,
        }),
      });
    }
    if (path.endsWith("/commands") && failNextDraftSave) {
      failNextDraftSave = false;
      return route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({ error: "Neutral concurrent edit fixture" }),
      });
    }
    if(path.includes('/contexts')) {
      const method=route.request().method();let value={contexts:savedContexts};
      if(path.endsWith('/link')) {const body=route.request().postDataJSON();value={...body,sha256:'a'.repeat(64)};}
      else if(method==='PUT'&&contextConflict){contextConflict=false;return route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({error:'Neutral saved context conflict'})});}
      else if(method==='POST'||method==='PUT'){
        const body=route.request().postDataJSON();value={id:'CTX-NEUTRAL',version:method==='POST'?1:2,status:'ACTIVE',user:body.payload,scope_status:'CURRENT',context_status:'CURRENT',engagement_revision:e.revision,link_status:body.payload.links.map(reference=>({reference,status:'EXACT_PIN_AVAILABLE'}))};savedContexts=[value];
      }
      return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(value)});
    }
    if(path.includes('/jobs')) {
      let value={jobs:[backgroundJob]};
      if(path.endsWith('/input')) {inputReads++; value={command_id:'queued-neutral',expected_revision:4,kind:'meeting.message',payload:{meeting_id:'MEET-01',content:'Neutral queued question retained across reload'}};}
      if(path.endsWith('/retry')) {
        const body=route.request().postDataJSON();
        if(body.observed_job_revision!==backgroundJob.job_revision)throw Error('Retry changed observed job version');
        exactRetries++; backgroundJob.status='RUNNING';backgroundJob.job_revision++;value=backgroundJob;
      }
      return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(value)});
    }
    if (path.includes("/instructor-key")) {
      ++instructorRequests;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          path.endsWith("/instructor-key") ? keyIndex : keyDetail,
        ),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        path === "/api/bootstrap"
          ? {
              viewer: {
                id: "fixture",
                display_name: "Layout fixture trainer",
                roles: ["trainer", "reviewer"],
              },
              csrf_token: "fixture",
              engagements: [e],
              capabilities: e.capabilities,
              programs: [
                { id: "SOC2", name: "SOC 2" },
                { id: "HIPAA", name: "HIPAA" },
              ],
              people: [],
              controls: [],
            }
          : e,
      ),
    });
  });
  for (const view of [
    "kickoff",
    "controls",
    "pbc",
    "meetings",
    "people",
    "populations",
    "notes",
    "calendar",
    "findings",
    "review",
  ]) {
    await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=${view}`);
    await page.locator(".workspace-footer").waitFor();
    await page.screenshot({
      path: `${output}/${view}-desktop.png`,
      fullPage: true,
    });
    if (
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      )
    )
      throw Error(`Overflow ${view}`);
  }
  // Table navigation retains only search/sort/page, never row data.
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=controls`);
  const controlTable = page
    .locator(".record-table")
    .filter({
      has: page.getByRole("button", { name: "Sort by Control", exact: true }),
    })
    .last();
  await controlTable.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: /PBC & evidence/ }).click();
  await page.getByRole("button", { name: /Controls & tracker/ }).click();
  if (!(await controlTable.innerText()).includes("Page 2 of 2"))
    throw Error("Table page lost across navigation");
  await controlTable.getByRole("searchbox").fill("unmatched-neutral-filter");
  await page.getByRole("button", { name: /PBC & evidence/ }).click();
  if (
    (await page
      .locator(".record-table")
      .first()
      .getByRole("searchbox")
      .inputValue()) !== ""
  )
    throw Error("Table search crossed collections");
  await page.getByRole("button", { name: /Controls & tracker/ }).click();
  if (
    (await controlTable.getByRole("searchbox").inputValue()) !==
    "unmatched-neutral-filter"
  )
    throw Error("Table search lost across navigation");
  await controlTable
    .getByRole("button", { name: "Clear table search", exact: true })
    .click();
  await controlTable.getByRole("button", { name: "CC-1", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Next record", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("heading", {
      name: "Access authorization and quarterly review 2",
      exact: true,
    })
    .waitFor();
  await page.keyboard.press("Escape");
  // Personal draft endpoints are mocked here; full page reload clears all client memory.
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=notes`);
  await page
    .getByRole("button", { name: "Add observation", exact: true })
    .click();
  let form = page.getByRole("dialog");
  await form.getByLabel("Control", { exact: true }).selectOption("CC-1");
  await form
    .getByLabel("Subject", { exact: true })
    .fill("Neutral draft subject");
  await form
    .getByLabel("Observation", { exact: true })
    .fill("Unsent draft observation");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: /Controls & tracker/ }).click();
  await page
    .getByRole("button", { name: /Notes/, exact: false })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Add observation", exact: true })
    .click();
  form = page.getByRole("dialog");
  if (
    (await form.getByLabel("Observation", { exact: true }).inputValue()) !==
    "Unsent draft observation"
  )
    throw Error("Closed note draft lost");
  await page.keyboard.press("Escape");
  await form.waitFor({ state: "detached" });
  await page.reload();
  await page
    .getByRole("button", { name: "Add observation", exact: true })
    .click();
  form = page.getByRole("dialog");
  await form.getByText("Personal draft restored.", { exact: false }).waitFor();
  if (
    (await form.getByLabel("Observation", { exact: true }).inputValue()) !==
    "Unsent draft observation"
  )
    throw Error("Reload lost saved personal draft");
  conflictNextPersonalDraft = true;
  await form
    .getByLabel("Observation", { exact: true })
    .fill("Local conflict text");
  await form
    .getByText("Another session changed this draft.", { exact: false })
    .waitFor();
  if (
    (await form.getByLabel("Observation", { exact: true }).inputValue()) !==
    "Local conflict text"
  )
    throw Error("Conflict overwrote local text");
  if (
    !(await form
      .getByRole("button", { name: "Save record", exact: true })
      .isDisabled())
  )
    throw Error("Conflict permitted formal save");
  await form
    .getByText("Inspect saved draft from the other session", { exact: true })
    .click();
  await form.getByText("Other session text", { exact: true }).waitFor();
  await form
    .getByRole("button", {
      name: "Keep this form; replace the inspected saved draft",
      exact: true,
    })
    .click();
  await form
    .getByText("Personal draft saved; not submitted as an audit record.", {
      exact: false,
    })
    .waitFor();
  await form
    .getByLabel("Observation", { exact: true })
    .fill("Unsent draft observation");
  failNextDraftSave = true;
  await form.getByRole("button", { name: "Save record", exact: true }).click();
  await page.getByRole("alert").waitFor();
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Add observation", exact: true })
    .click();
  form = page.getByRole("dialog");
  if (
    (await form.getByLabel("Observation", { exact: true }).inputValue()) !==
    "Unsent draft observation"
  )
    throw Error("Failed save erased draft");
  await form.getByRole("button", { name: "Save record", exact: true }).click();
  await form.waitFor({ state: "detached" });
  await page
    .getByRole("button", { name: "Add observation", exact: true })
    .click();
  form = page.getByRole("dialog");
  if (
    (await form.getByLabel("Observation", { exact: true }).inputValue()) !== ""
  )
    throw Error("Successful save retained stale draft");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: /Workpapers & review/ }).click();
  await page
    .getByRole("button", { name: "New structured workpaper", exact: true })
    .click();
  form = page.getByRole("dialog");
  await form
    .getByLabel("Workpaper title", { exact: true })
    .fill("Unsent new workpaper");
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "New structured workpaper", exact: true })
    .click();
  form = page.getByRole("dialog");
  if (
    (await form.getByLabel("Workpaper title", { exact: true }).inputValue()) !==
    "Unsent new workpaper"
  )
    throw Error("New workpaper draft lost");
  await form
    .getByRole("button", { name: "Discard unsaved draft", exact: true })
    .click();
  await page.waitForFunction(
    () =>
      document.querySelector('input[aria-label="Workpaper title"]')?.value ===
      "",
  );
  await page.keyboard.press("Escape");
  const openPaperDraft = async () => {
    await page.keyboard.press("Control+k");
    await page
      .getByRole("searchbox", { name: "Search this engagement" })
      .fill("W-01");
    await page
      .getByRole("button", { name: "Search records", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Preview W-01", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Save new version", exact: true })
      .click();
  };
  await openPaperDraft();
  form = page.getByRole("dialog");
  await form
    .getByLabel("Objective", { exact: true })
    .fill("Unsent successor objective");
  await page.keyboard.press("Escape");
  e.workpapers[0].versions = [
    { version: 1, objective: "Original objective" },
    {
      version: 2,
      objective: "Concurrent saved objective",
      procedures: "Current procedure",
      conclusion: "OPEN",
      text: "Current base",
    },
  ];
  e.revision += 1;
  await page.evaluate(() => dispatchEvent(new PopStateEvent("popstate")));
  await page.getByText(`revision ${e.revision}`, { exact: false }).waitFor();
  await openPaperDraft();
  form = page.getByRole("dialog");
  await form.getByText("Stale base:", { exact: false }).waitFor();
  if (
    !(await form
      .getByRole("button", { name: "Save record", exact: true })
      .isDisabled())
  )
    throw Error("Stale draft remained submittable");
  await form.getByText("Inspect current saved base", { exact: true }).click();
  await form.getByText("Concurrent saved objective", { exact: true }).waitFor();
  await form
    .getByRole("button", {
      name: "I reviewed the current base; use this draft",
      exact: true,
    })
    .click();
  if (
    (await form.getByLabel("Objective", { exact: true }).inputValue()) !==
    "Unsent successor objective"
  )
    throw Error("Explicit stale draft rebase lost text");
  await page.keyboard.press("Escape");
  // Search previews resolve actual current public records; no instructor fields enter search.
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=controls`);
  const search = page.getByRole("searchbox", {
    name: "Search this engagement",
  });
  await page.getByText("Find related work", {exact:false}).waitFor();
  await page.keyboard.press("Control+k");
  await search.fill("CC-1");
  await page
    .getByRole("button", { name: "Search records", exact: true })
    .click();
  await page.getByRole("button", { name: "Preview CC-1", exact: true }).click();
  await page.getByRole("dialog").waitFor();
  if (
    !(await page.getByRole("dialog").textContent()).includes(
      "Access authorization",
    )
  )
    throw Error("Control search preview mismatched row");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Reset search", exact: true }).click();
  if ((await search.inputValue()) !== "")
    throw Error("Search reset lost input state");
  await search.fill("unmatched neutral phrase");
  await page
    .getByRole("button", { name: "Search records", exact: true })
    .click();
  await page
    .getByText(
      "No matches in the current authorized records and selected type.",
      { exact: false },
    )
    .waitFor();
  await page.getByRole("button", { name: "Reset search", exact: true }).click();
  // Existing Detail singular mapping must handle notes and tasks from unified search.
  for (const id of ["N-01", "T-01", "W-01"]) {
    await search.fill(id);
    await page
      .getByRole("button", { name: "Search records", exact: true })
      .click();
    await page
      .getByRole("button", { name: `Preview ${id}`, exact: true })
      .click();
    await page.getByRole("dialog").waitFor();
    if (!(await page.getByRole("dialog").textContent()).includes(id))
      throw Error(`Missing ${id} preview identity`);
    await page.keyboard.press("Escape");
  }
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=review`);
  const instructor = page.getByRole("region", {
    name: "Protected instructor source archive",
  });
  await instructor
    .getByRole("button", { name: keyEntry.id, exact: true })
    .click();
  const explanation = page.getByRole("article", {
    name: "Selected instructor explanation",
  });
  await explanation.waitFor();
  if (
    !(await explanation.textContent()).includes("UNVALIDATED") ||
    !(await explanation.textContent()).includes("NOT_BOUND")
  )
    throw Error("Instructor source limitations missing");
  await explanation.getByText("Facts", { exact: true }).click();
  await explanation
    .getByText("Neutral archived fact", { exact: true })
    .waitFor();
  await explanation
    .getByText("Acceptable alternatives", { exact: true })
    .click();
  await explanation
    .getByText("Further neutral inquiry", { exact: true })
    .waitFor();
  await instructor.getByLabel("Search source ID or review gap").fill("absent");
  await instructor
    .getByText("No matching archived explanations.", { exact: false })
    .waitFor();
  await instructor
    .getByRole("button", { name: "Reset filters", exact: true })
    .click();
  // Client absence check complements separate backend403 tests; mock does not establish server authorization.
  const priorInstructorRequests = instructorRequests;
  e.permissions = ["learn"];
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=review`);
  await page.locator(".workspace-footer").waitFor();
  if (
    (await page
      .getByRole("region", { name: "Protected instructor source archive" })
      .count()) ||
    instructorRequests !== priorInstructorRequests
  )
    throw Error("Learner requested protected archive");
  if (
    (await page.locator("body").textContent()).includes("Neutral archived fact")
  )
    throw Error("Learner DOM retained instructor fixture");
  e.permissions = ["instruct", "review", "learn"];
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=pbc`);
  await page.locator(".workspace-footer").waitFor();
  await page
    .getByRole("button", { name: "New PBC request +", exact: true })
    .click();
  await page.getByRole("dialog").waitFor();
  await page.keyboard.press("Escape");
  if (await page.getByRole("dialog").count())
    throw Error("Escape did not close dialog");
  // Actual App navigation on the same page; API remains a neutral mocked fixture.
  await page.getByRole("button", { name: /Controls & tracker/ }).click();
  await page.getByLabel("Program view").selectOption("SOC2");
  await page.getByRole("button", { name: /PBC & evidence/ }).click();
  await page.goBack();
  await page.getByLabel("Program view").waitFor();
  if ((await page.getByLabel("Program view").inputValue()) !== "SOC2")
    throw Error("Back lost program filter");
  await page
    .getByRole("button", { name: /Notes/, exact: false })
    .first()
    .click();
  await page.getByLabel("Search central notes").fill("neutral investigation");
  await page.getByRole("button", { name: /Controls & tracker/ }).click();
  await page
    .getByRole("button", { name: /Notes/, exact: false })
    .first()
    .click();
  if (
    (await page.getByLabel("Search central notes").inputValue()) !==
    "neutral investigation"
  )
    throw Error("Navigation lost notes filter");
  await page.getByRole("button", { name: /Meetings · MRL/ }).click();
  await page.getByLabel("Ask the owner").fill("Unsent neutral question");
  await page.getByRole("button", { name: /Controls & tracker/ }).click();
  await page.getByRole("button", { name: /Meetings · MRL/ }).click();
  if (
    (await page.getByLabel("Ask the owner").inputValue()) !==
    "Unsent neutral question"
  )
    throw Error("Same engagement lost conversation draft");
  const orientation = page.getByLabel("Current engagement context");
  if (!(await orientation.textContent()).includes("2027-12-31"))
    throw Error("Missing period orientation");
  await page.evaluate(() => {
    history.pushState({}, "", "/");
    dispatchEvent(new PopStateEvent("popstate"));
  });
  await page.getByRole("button", { name: /New engagement/i }).waitFor();
  if (await page.getByLabel("Current engagement context").count())
    throw Error("List retained prior engagement");
  let releaseSlow;
  const slow = new Promise((resolve) => {
    releaseSlow = resolve;
  });
  let slowStarted;
  const started = new Promise((resolve) => {
    slowStarted = resolve;
  });
  await page.route("**/api/engagements/ENG-SLOW", async (route) => {
    slowStarted();
    await slow;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ...e,
        id: "ENG-SLOW",
        title: "Delayed engagement",
      }),
    });
  });
  await page.evaluate(() => {
    history.pushState({}, "", "?engagement=ENG-SLOW&view=kickoff");
    dispatchEvent(new PopStateEvent("popstate"));
  });
  await started;
  await page.evaluate(() => {
    history.pushState({}, "", "/");
    dispatchEvent(new PopStateEvent("popstate"));
  });
  await page.getByRole("button", { name: /New engagement/i }).waitFor();
  releaseSlow();
  await page.waitForTimeout(150);
  if (await page.getByLabel("Current engagement context").count())
    throw Error("Late engagement response reopened abandoned scope");
  await page.goto(
    `http://127.0.0.1:5193/?engagement=${e.id}&view=pbc&kind=artifacts&object=unavailable-id`,
  );
  await page.getByRole("alert").waitFor();
  if (await page.getByLabel("Current engagement context").count())
    throw Error("Unavailable deep link exposed workspace");
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=pbc`);
  await page.locator(".workspace-footer").waitFor();
  await page.addStyleTag({
    content:
      ".rail{position:static;width:auto;min-height:0;padding:14px;display:flex;flex-wrap:wrap;gap:12px}.rail nav{display:flex;flex-wrap:wrap}.rail footer,.rail-label,.engagement-switch{display:none}.main-shell{margin-left:0}.app{display:block}.brand{width:190px}.rail nav button{padding:8px}.topbar{height:48px}",
  });
  await page.screenshot({
    path: `${output}/candidate-horizontal-workroom.png`,
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=pbc`);
  await page.locator(".workspace-footer").waitFor();
  await page.screenshot({ path: `${output}/pbc-narrow.png`, fullPage: true });
  if (
    await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)
  )
    throw Error("Narrow overflow");
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.goto("http://127.0.0.1:5193");
  await page.getByRole("button", { name: /New engagement/i }).click();
  await page.getByRole("button", { name: /Messy Authored/ }).click();
  await page.getByRole("button", { name: /Continue/ }).click();
  await page.screenshot({
    path: `${output}/configuration-desktop.png`,
    fullPage: true,
  });
  e.capabilities.background_jobs=true;
  await page.setViewportSize({width:1440,height:1050});
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=controls`);
  await page.getByText('Company replies and background work',{exact:true}).click();
  let background=page.getByRole('region',{name:'Background work'});
  await background.getByText('RUNNING',{exact:true}).waitFor();
  await page.getByRole('button',{name:/Notes/}).first().click();
  await background.getByText('RUNNING',{exact:true}).waitFor();
  await page.reload();
  await page.getByText('Company replies and background work',{exact:true}).click();
  background=page.getByRole('region',{name:'Background work'});
  await background.getByText('RUNNING',{exact:true}).waitFor();
  if(inputReads!==0)throw Error('List eagerly fetched private queued questions');
  backgroundJob.status='INTERRUPTED';backgroundJob.job_revision=3;
  await background.getByText('INTERRUPTED',{exact:true}).waitFor();
  const retry=background.getByRole('button',{name:'Retry original command',exact:true});
  if(await retry.isEnabled())throw Error('Retry enabled without inspection');
  if(await background.getByRole('checkbox').isEnabled())throw Error('Inspection checkbox enabled before input read');
  await background.getByRole('button',{name:'Inspect queued question',exact:true}).click();
  await background.getByText('Neutral queued question retained across reload',{exact:true}).waitFor();
  await background.getByRole('checkbox').check();
  await retry.click();
  await background.getByText('RUNNING',{exact:true}).waitFor();
  if(inputReads!==1||exactRetries!==1)throw Error('Inspection/retry identity mismatch');
  backgroundJob.status='CONFLICTED';backgroundJob.job_revision=5;
  await background.getByText('CONFLICTED',{exact:true}).waitFor();
  if(await background.getByRole('button',{name:'Retry original command',exact:true}).count())throw Error('Conflicted command offered rebase/retry');
  await page.screenshot({path:`${output}/background-work-desktop.png`,fullPage:true});
  await page.getByRole('button',{name:/Meetings · MRL/}).click();
  let acceptQueued; const acceptance=new Promise(resolve=>{acceptQueued=resolve;});
  let sentQueued; const sent=new Promise(resolve=>{sentQueued=resolve;});
  let submittedEnvelope;
  await page.route(`**/api/engagements/${e.id}/jobs`,async route=>{
    if(route.request().method()!=='POST')return route.fallback();
    submittedEnvelope=route.request().postDataJSON();sentQueued();await acceptance;
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...backgroundJob,status:'RUNNING'})});
  });
  await page.getByLabel('Ask the owner').fill('First queued question');
  await page.getByRole('button',{name:'Send message',exact:true}).click();await sent;
  await page.getByLabel('Ask the owner').fill('Next question typed during acceptance');
  acceptQueued();
  await page.waitForTimeout(150);
  if(await page.getByLabel('Ask the owner').inputValue()!=='Next question typed during acceptance')throw Error('Delayed acceptance cleared newer meeting draft');
  if(submittedEnvelope.payload.content!=='First queued question'||!submittedEnvelope.command_id)throw Error('Background submission changed original envelope');
  e.capabilities.workspace_contexts=true;
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=controls`);
  await page.getByText('Saved investigations',{exact:true}).first().click();
  let investigations=page.getByRole('region',{name:'Saved investigations'});
  await investigations.getByLabel('Investigation title',{exact:true}).fill('Neutral explicit investigation');
  await investigations.getByLabel('Your investigation question',{exact:true}).fill('Which record supports this decision?');
  await investigations.getByLabel('Your next step',{exact:true}).fill('Inspect the selected control');
  await investigations.getByLabel('Existing record',{exact:false}).selectOption('CC-1');
  await investigations.getByRole('button',{name:'Pin selected record',exact:true}).click();
  await investigations.getByRole('button',{name:'Remove link CC-1',exact:true}).waitFor();
  await investigations.getByRole('button',{name:'Save investigation',exact:true}).click();
  await investigations.getByText('Neutral explicit investigation',{exact:true}).waitFor();
  await page.reload();
  await page.getByText('Saved investigations',{exact:true}).first().click();
  investigations=page.getByRole('region',{name:'Saved investigations'});
  await investigations.getByText('Which record supports this decision?',{exact:true}).waitFor();
  await investigations.getByRole('button',{name:'Open current record',exact:true}).click();
  await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');
  await investigations.getByRole('button',{name:'Edit saved investigation',exact:true}).click();
  await page.screenshot({path:`${output}/context-editor-debug.png`,fullPage:true});
  await investigations.getByLabel('Your investigation question',{exact:true}).fill('Unsaved explicit correction');
  contextConflict=true;
  await investigations.getByRole('button',{name:'Save investigation',exact:true}).click();
  await investigations.getByRole('alert').waitFor();
  if(await investigations.getByLabel('Your investigation question',{exact:true}).inputValue()!=='Unsaved explicit correction')throw Error('Context conflict discarded editor');
  if(await investigations.getByRole('button',{name:'Save investigation',exact:true}).isEnabled())throw Error('Context conflict allowed silent overwrite');
  if(await investigations.getByRole('button',{name:'Edit saved investigation',exact:true}).isEnabled())throw Error('Dirty context allowed silent editor switch');
  await investigations.getByRole('button',{name:'Discard editor and start new investigation',exact:true}).click();
  savedContexts[0].link_status[0].status='CONTENT_CHANGED';
  await page.reload();
  await page.getByText('Saved investigations',{exact:true}).first().click();
  investigations=page.getByRole('region',{name:'Saved investigations'});
  if(await investigations.getByRole('button',{name:'Open current record',exact:true}).isEnabled())throw Error('Changed context source remained clickable');
  savedContexts[0].link_status[0].status='EXACT_PIN_AVAILABLE';
  savedContexts[0].context_status='CONTEXT_CHANGED';
  await page.reload();
  await page.getByText('Saved investigations',{exact:true}).first().click();
  investigations=page.getByRole('region',{name:'Saved investigations'});
  await investigations.getByText(/Company source and permission context: CONTEXT_CHANGED/).waitFor();
  if(await investigations.getByRole('button',{name:'Open current record',exact:true}).isEnabled())throw Error('Changed basis opened exact pin');
  await investigations.getByRole('button',{name:'Edit saved investigation',exact:true}).click();
  if(await investigations.getByRole('button',{name:'Save investigation',exact:true}).isEnabled())throw Error('Changed basis saved without explicit review');
  await investigations.getByRole('checkbox').check();
  await investigations.getByRole('button',{name:'Save investigation',exact:true}).click();
  await investigations.getByRole('button',{name:'Open current record',exact:true}).waitFor({state:'visible'});
  await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='Open current record'&&!b.disabled));
  await page.screenshot({path:`${output}/saved-investigations-desktop.png`,fullPage:true});
  // Exact readiness DTO; no invented assurance score or excluded denominator removal.
  let wrongStatusRevision=false, delayStatus=false, releaseStatus, statusStarted;
  const delayedStatus=new Promise(resolve=>{releaseStatus=resolve;});
  const startedStatus=new Promise(resolve=>{statusStarted=resolve;});
  await page.route(`**/api/engagements/${e.id}/work-status`,async route=>{
    const response={schema_version:'1.0',engagement_id:e.id,engagement_revision:e.revision+(wrongStatusRevision?1:0),status:'OBSERVABLE_ADMINISTRATIVE_PROGRESS_ONLY',scope_sha256:'b'.repeat(64),denominators:{scoped_controls:32,scoped_procedures:3,known_not_applicable_tasks:1,unassigned_or_out_of_scope_tasks:2},limits:['Collected files do not establish effectiveness.'],controls:[{control:{kind:'control',id:'CC-1'},procedure_denominator:3,reasons:[{code:'PROVISIONAL_POPULATION',references:[{kind:'task',id:'T-01'}]}],procedures:[{task:{kind:'task',id:'T-01'},recorded_status:'NOT_APPLICABLE',recorded_conclusion:'NOT_ASSESSED'}],sources:[{artifact:{kind:'artifact',id:'A-01',sha256:'a'.repeat(64)},qualifiers:[{field:'origin',value:'OPERATOR_SUPPLIED'}]}]}]};
    if(delayStatus){statusStarted();await delayedStatus;}
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(response)});
  });
  await page.getByText('Recorded work and open dependencies',{exact:true}).click();
  const work=page.locator('.work-status');
  await work.getByRole('button',{name:'Check work status',exact:true}).click();
  await work.getByText(/32 scoped controls.*3 assigned procedures.*2 unassigned/).waitFor();
  await work.getByText(/procedure count includes 1 recorded exclusions/).waitFor();
  await work.getByLabel('Inspect control status',{exact:true}).selectOption('CC-1');
  await work.getByText('Exact procedure and source records',{exact:true}).click();
  await work.getByRole('button',{name:'Open task T-01',exact:true}).last().click();
  await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');
  await work.getByRole('button',{name:'Open artifact A-01',exact:true}).click();
  await page.getByRole('dialog').waitFor();
  if(!(await page.getByRole('dialog').textContent()).includes('access-review-population.csv'))throw Error('Readiness source preview changed identity');
  await page.keyboard.press('Escape');
  await page.screenshot({path:`${output}/work-status-desktop.png`,fullPage:true});
  wrongStatusRevision=true;
  await work.getByRole('button',{name:'Check work status',exact:true}).click();
  await work.getByRole('alert').waitFor();
  if(await work.getByText(/32 scoped controls/).count())throw Error('Outdated response retained prior denominator');
  wrongStatusRevision=false;delayStatus=true;
  await work.getByRole('button',{name:'Check work status',exact:true}).click();await startedStatus;
  await page.getByRole('button',{name:/Notes/}).first().click();
  releaseStatus();await page.waitForTimeout(120);
  if(await page.getByText(/32 scoped controls/).count())throw Error('Late status report reopened hidden controls');
  const originalPermissions=e.permissions;e.permissions=[];
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=controls`);
  await page.getByLabel('Current engagement context').waitFor();
  if(await page.locator('.work-status').count())throw Error('Work status displayed without current permissions');
  e.permissions=originalPermissions;
  e.capabilities.work_status=false;
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=controls`);
  await page.getByLabel('Current engagement context').waitFor();
  if(await page.locator('.work-status').count())throw Error('Unsupported work-status capability exposed panel');
  e.capabilities.work_status=true;


  // Protected neutral bound reference, separate historical comparison selection.
  e.capabilities.bound_instructor_keys=true;
  const boundFixture={binding:{manifest_sha256:'d'.repeat(64),engagement_id:e.id,bound_revision:0,current_revision:e.revision,status:'HISTORICAL_REVISION'},snapshot:{status:'BOUND_INSTRUCTOR_AUTHORED_UNVALIDATED',professional_validation:'UNVALIDATED',authored_status:'INSTRUCTOR_AUTHORED_INFERENCE',grading:'NOT_PERFORMED',audited_actor_id:'LEARNER-NEUTRAL',created_at:'2027-02-12T09:00:00Z',operator_source_as_of:'2027-02-12T09:00:00Z',engagement:{id:e.id,revision:0,scope:e.scope,simulated_at:e.simulated_at,state_sha256:'a'.repeat(64),history_sha256:'b'.repeat(64)},sources:[],software_verified:['Exact source metadata'],limits:['Unvalidated instructor interpretation'],authored:{issues:[{id:'I1',control_ids:['CC-1'],source_ids:[],claim:'Neutral authored interpretation',uncertainty:'Requires review'}],expectations:[{id:'E1',issue_ids:['I1'],procedure:'Inspect explicit evidence links',acceptable_alternatives:['Other authorized corroboration']}],uncertainty:[],source_pins:{}}}};
  let comparisonMode='normal';let requestedHistory;
  await page.route(`**/api/engagements/${e.id}/instructor-binding`,route=>route.fulfill({contentType:'application/json',body:JSON.stringify(boundFixture)}));
  await page.route(`**/api/engagements/${e.id}/instructor-comparison?*`,route=>{
    requestedHistory=Number(new URL(route.request().url()).searchParams.get('revision'));
    const value={status:comparisonMode==='mismatch'?'CONTEXT_MISMATCH':'DETERMINISTIC_LINK_INVENTORY_ONLY',engagement_id:e.id,audited_actor_id:'LEARNER-NEUTRAL',binding_manifest_sha256:(comparisonMode==='changed'?'f':'d').repeat(64),bound_revision:0,selected_history_revision:requestedHistory,current_revision:e.revision,selected_state_sha256:'a'.repeat(64),selected_history_sha256:'b'.repeat(64),selected_history_tip_sha256:'c'.repeat(64),grading:'NOT_PERFORMED',professional_validation:'UNVALIDATED',mismatches:comparisonMode==='mismatch'?['CURRENT_COMPANY_BASIS_DIFFERS_FROM_BOUND_SOURCE']:[],limits:['No inspection or sufficiency determination'],sources:[],audited_actor_activity:[{revision:1,command_id:'NEUTRAL1',kind:'note.create'}],shared_workspace_activity_count:2,expectations:[{expectation_id:'E1',status:'NO_EXPLICIT_WORKPAPER_SOURCE_LINK_RECORDED',source_linked_workpaper_versions:[],workpaper_version_reviews:[],source_linked_populations:[],population_linked_selections:[],control_associated_records_only:{requests:[],tasks:[{id:'T-01',recorded_status:'COMPLETE'}]}}]};
    return route.fulfill({contentType:'application/json',body:JSON.stringify(value)});
  });
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=review`);
  await page.getByText('Trace recorded work against bound expectations',{exact:true}).click();
  const comparison=page.locator('.instructor-comparison');
  await comparison.getByLabel('History revision',{exact:true}).fill('1');
  await comparison.getByRole('button',{name:'Trace recorded links',exact:true}).click();
  await comparison.getByText(/1 recorded commands by the audited actor.*2 by other actors/).waitFor();
  if(requestedHistory!==1)throw Error('Comparison silently selected current history');
  await comparison.getByLabel('Bound expectation',{exact:true}).selectOption('E1');
  await comparison.getByText(/This does not establish a missed issue/).waitFor();
  await comparison.getByText(/Control-associated procedures · 1/).click();
  await comparison.getByText('T-01',{exact:true}).waitFor();
  comparisonMode='mismatch';
  await comparison.getByRole('button',{name:'Trace recorded links',exact:true}).click();
  await comparison.getByText(/Record comparison is withheld/).waitFor();
  if(await comparison.getByLabel('Bound expectation',{exact:true}).count())throw Error('Mismatch exposed expectation comparison');
  comparisonMode='changed';
  await comparison.getByRole('button',{name:'Trace recorded links',exact:true}).click();
  await comparison.getByRole('alert').waitFor();
  if(await comparison.getByText(/recorded commands by the audited actor/).count())throw Error('Changed manifest retained comparison');
  if (errors.length) throw Error(errors.join("\n"));
  await writeFile(
    `${output}/browser-receipt.json`,
    JSON.stringify(
      {
        fixture:
          "Public synthetic layout data; API mocked; not a backend acceptance claim",
        views: 10,
        comparison_checks:['explicit historical revision preserved','audited vs shared commands distinct','missing link not missedissue inference','context mismatch withholds all comparisons','changed bound manifest rejected'],
        work_status_checks:['exact denominators retain exclusions','selected control procedure and source previews','outdated revision clears previous report','late response after section exit discarded','no status panel without current engagement permissions'],
        investigation_checks:['explicit user question/link save and reload','current pinned record preview','409 retains unsaved editor without overwrite','changed source pin non-clickable','dirty editor prevents silent investigation switch','changed branch/acquisition/permission basis blocks exact pin until explicit review/save'],
        background_checks: ['pending navigation and reload continuity','no eager queued input reads','explicit exact question inspection gates retry','observed job revision retained','conflicted job never retries','delayed acceptance preserves newly typed next question'],
        draft_checks: [
          "new note close/reopen and section continuity",
          "full reload recovers saved personal draft via endpoint",
          "409draft conflict retains local text and requires explicit inspected choice",
          "failed save retains draft",
          "successful save clears saved draft",
          "new workpaper and explicit discard",
          "stale successor base disables save until explicit review",
        ],
        search_checks: [
          "control/note/task/workpaper preview identity",
          "reset and empty-state filters",
        ],
        instructor_checks: [
          "exact index/detail payload",
          "unbound/unvalidated labels",
          "facts/alternative drilldown",
          "filter reset",
          "no learner component/request/private DOM",
        ],
        navigation_checks: [
          "program filter survives browser back",
          "notes search survives section navigation",
          "scope orientation",
          "conversation draft survives same-engagement navigation",
          "late engagement response cannot reopen abandoned scope",
          "popstate to list clears engagement",
          "unavailable object deep link fails closed",
        ],
        desktop: [1440, 1050],
        narrow: [390, 844],
        page_errors: errors,
      },
      null,
      2,
    ),
  );
  console.log(
    "10 sections, configuration, desktop/narrow: browser checks passed",
  );
} finally {
  await browser?.close();
  server.kill();
}
