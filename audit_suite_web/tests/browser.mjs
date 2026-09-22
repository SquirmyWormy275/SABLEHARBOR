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
      instructor_reference_library: true,
      personal_drafts: true,
      workpaper_procedure_links: true,
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
          { role_ref: "Neutral owner", beliefs: ["Authored statement only"], knows_fact_ids: ["F1"] },
        ],
        artifacts: [{ id: "A1", name: "neutral.txt" }],
        events: [{ id: "E1", trigger: "REQUEST", offset_business_days: 0 }],
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
        nodes: [
          { id: "fact:F1", kind: "fact", source_pointer: "/facts/0" },
          { id: "actor:0", kind: "actor", source_pointer: "/actor_knowledge/0" },
          { id: "event:E1", kind: "event", source_pointer: "/events/0" },
          { id: "path:P1", kind: "path", source_pointer: "/playable_paths/0" },
        ],
        edges: [{ from: "actor:0", to: "fact:F1", relation: "AUTHORED_KNOWLEDGE", source_pointer: "/actor_knowledge/0/knows_fact_ids/0" }],
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
      if(path.endsWith('/input')) {inputReads++; value={command_id:'queued-neutral',expected_revision:4,kind:'meeting.message',payload:{meeting_id:'MEET-01',content:'Neutral queued question retained across reload',source_records:[{system_id:'owned:SYS',record_id:'PINNED-QUEUED',version:3,sha256:'d'.repeat(64)}]}};}
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
              background_command_kinds:e.background_command_kinds??[],
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
  await form.getByLabel('Control',{exact:true}).selectOption('CC-1');
  await form.getByLabel('Support procedure',{exact:true}).selectOption('T-01');
  await form.getByRole('button',{name:'Link selected procedure to this version',exact:true}).click();
  await form.getByRole('button',{name:'Remove procedure T-01',exact:true}).waitFor();

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
  await form.getByRole('button',{name:'Remove procedure T-01',exact:true}).waitFor();
  if(await form.getByLabel('Control',{exact:true}).inputValue()!=='CC-1')throw Error('Procedure draft lost scoped control');
  await form.getByRole('button',{name:'Remove procedure T-01',exact:true}).click();

  // Artifact context must restore the personal draft before an explicit source link.
  await page.keyboard.press("Escape");
  e.artifacts[0].status="AVAILABLE"; e.requests[0].purpose="Neutral recorded inspection purpose"; e.requests[0].control_id="CC-1"; e.revision++;
  await page.evaluate(()=>dispatchEvent(new PopStateEvent("popstate")));
  await page.getByText(`revision ${e.revision}`,{exact:false}).waitFor();
  await page.keyboard.press("Control+k");
  await page.getByRole("searchbox",{name:"Search this engagement"}).fill("A-01");
  await page.getByRole("button",{name:"Search records",exact:true}).click();
  await page.getByRole("button",{name:"Preview A-01",exact:true}).click();
  await page.getByText("Neutral recorded inspection purpose",{exact:true}).waitFor();
  await page.getByRole("button",{name:"Open request PBC-01",exact:true}).click();
  await page.getByRole("button",{name:"Back to artifact A-01",exact:true}).click();
  await page.getByRole("button",{name:"Hide recorded context",exact:true}).click();
  await page.getByRole("button",{name:"Show recorded context",exact:true}).click();
  await page.getByRole("button",{name:"Open workpaper draft",exact:true}).click();
  form=page.getByRole("dialog");
  await form.getByText("Personal draft restored.",{exact:false}).waitFor();
  if(await form.getByLabel("Workpaper title",{exact:true}).inputValue()!=="Unsent new workpaper")throw Error("Evidence handoff overwrote personal draft");
  if((await form.getByLabel("Evidence references",{exact:true}).inputValue()).includes("A-01"))throw Error("Evidence automatically promoted into draft");
  await form.getByRole("button",{name:"Add this original to draft",exact:true}).click();
  await form.getByRole("button",{name:"Add this original to draft",exact:true}).click();
  if(await form.getByLabel("Evidence references",{exact:true}).inputValue()!=="A-01")throw Error("Explicit source append duplicated or replaced fields");
  await form.getByRole("button",{name:"Close (keep draft)",exact:true}).click();
  await page.getByRole("button",{name:"Open workpaper draft",exact:true}).click();
  form=page.getByRole("dialog");await form.getByText("Personal draft restored.",{exact:false}).waitFor();
  if(await form.getByLabel("Workpaper title",{exact:true}).inputValue()!=="Unsent new workpaper" || await form.getByLabel("Evidence references",{exact:true}).inputValue()!=="A-01")throw Error("Draft source/text lost after return");

  for (const authorityChange of ["scope", "permission"]) {
    const oldScope=e.scope, oldPermissions=e.permissions;
    if(authorityChange==="scope")e.scope={...e.scope,period_start:"2027-01-02"};else e.permissions=["review"];
    e.revision++;
    await page.evaluate(()=>dispatchEvent(new PopStateEvent("popstate")));
    await page.getByText(`revision ${e.revision}`,{exact:false}).waitFor();
    await page.waitForFunction(()=>document.querySelectorAll('dialog[open]').length===0);
    if(await page.getByRole("button",{name:"Add this original to draft",exact:true}).count())throw Error("Changed authority retained a handoff action");
    if(!JSON.stringify([...personalDrafts.values()]).includes("Unsent new workpaper"))throw Error("Authority change erased persisted draft");
    e.scope=oldScope;e.permissions=oldPermissions;e.revision++;
    await page.evaluate(()=>dispatchEvent(new PopStateEvent("popstate")));
    await page.getByText(`revision ${e.revision}`,{exact:false}).waitFor();
    await page.keyboard.press("Control+k");
    await page.getByRole("searchbox",{name:"Search this engagement"}).fill("A-01");
    await page.getByRole("button",{name:"Search records",exact:true}).click();
    await page.getByRole("button",{name:"Preview A-01",exact:true}).click();
    await page.getByRole("button",{name:"Open workpaper draft",exact:true}).click();
    form=page.getByRole("dialog");await form.getByText("Personal draft restored.",{exact:false}).waitFor();
    if(await form.getByLabel("Workpaper title",{exact:true}).inputValue()!=="Unsent new workpaper")throw Error("Scoped draft failed restore after original authority returned");
  }
  e.company_source_binding={company:"fixture",branch:"changed-source"}; e.revision++;
  await page.evaluate(()=>dispatchEvent(new PopStateEvent("popstate")));
  await page.getByText(`revision ${e.revision}`,{exact:false}).waitFor();
  await form.getByText("Source context changed. Reopen the current original before linking it.",{exact:true}).waitFor();
  if(!await form.getByRole("button",{name:"Add this original to draft",exact:true}).isDisabled())throw Error("Changed source permitted stale link");
  await form.getByRole("button",{name:"Close (keep draft)",exact:true}).click();
  if(await page.getByRole("button",{name:"Open workpaper draft",exact:true}).count())throw Error("Close reopened obsolete artifact context");
  await page.getByRole("button",{name:"New structured workpaper",exact:true}).click();
  form=page.getByRole("dialog");await form.getByText("Personal draft restored.",{exact:false}).waitFor();
  if(await form.getByLabel("Workpaper title",{exact:true}).inputValue()!=="Unsent new workpaper")throw Error("Context change destroyed saved draft");

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
  await explanation.locator("summary").getByText("Facts", { exact: true }).click();
  await explanation
    .getByText("Neutral archived fact", { exact: true })
    .waitFor();
  await explanation
    .getByText("Acceptable alternatives", { exact: true })
    .click();
  await explanation
    .getByText("Further neutral inquiry", { exact: true })
    .waitFor();
  const relationships = explanation.getByRole("region", { name: "Authored relationship explorer" });
  await relationships.getByRole("button", { name: "actor:0", exact: true }).click();
  const selectedNode = relationships.getByRole("article", { name: "Selected authored node" });
  await selectedNode.getByRole("button", { name: "fact:F1", exact: true }).click();
  await selectedNode.getByRole("heading", { name: "fact:F1", exact: true }).waitFor();
  await relationships.getByLabel("Find a relationship node").fill("no-match");
  await selectedNode.getByText("The selected node is outside the current search.", { exact: false }).waitFor();
  await selectedNode.getByRole("button", { name: "Back through relationships" }).click();
  await selectedNode.getByRole("heading", { name: "actor:0", exact: true }).waitFor();
  await relationships.getByLabel("Find a relationship node").fill("");
  await relationships.getByText("Event timing by trigger", { exact: true }).click();
  await relationships.getByText("REQUEST · 0 business days from this trigger", { exact: true }).waitFor();
  await relationships.getByRole("button", { name: "path:P1", exact: true }).click();
  await selectedNode.getByText("No explicit links were authored for this node.", { exact: false }).waitFor();
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
  e.capabilities.company_message_sources=true;e.meetings[0].person_id='P-01';e.meetings.push({id:'M-OTHER',title:'Other participant meeting',person_id:'P-02',messages:[],status:'OPEN'});
  await page.route(`**/api/engagements/${e.id}/company/systems`,route=>route.fulfill({contentType:'application/json',body:JSON.stringify({systems:[{system:'owned:SYS',owner:'P-01'},{system:'other:SYS',owner:'P-02'}],registry_sha256:'c'.repeat(64)})}));
  await page.route(`**/api/engagements/${e.id}/company/systems/*/records?*`,route=>route.fulfill({contentType:'application/json',body:JSON.stringify({records:[1,2].map(n=>({company:'NEUTRAL',branch:'B',system:'SYS',record:'REC-'+n,version:n,sha256:String(n).repeat(64),registry_sha256:'c'.repeat(64),source_system_alias:'owned:SYS'})),registry_sha256:'c'.repeat(64),next_after_record:null})}));
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
  await background.getByText(/owned:SYS \/ PINNED-QUEUED/).waitFor();
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
  await page.getByText('Choose exact company records for this question',{exact:true}).click();
  await page.getByRole('button',{name:"Load participant's source systems",exact:true}).click();
  const sourceSystem=page.getByLabel('Participant source system',{exact:true});await sourceSystem.selectOption('owned:SYS');
  if(await sourceSystem.locator('option[value="other:SYS"]').count())throw Error('Picker exposed another participant system');
  await page.getByRole('button',{name:'Load source records',exact:true}).click();
  await page.getByRole('button',{name:'Use record REC-1 version 1',exact:true}).click();
  let releaseOldSources,oldSourcesRequested;const oldSourcesWait=new Promise(r=>{releaseOldSources=r;}),oldSourcesSeen=new Promise(r=>{oldSourcesRequested=r;});let oldSourceOnce=true;
  await page.route(`**/api/engagements/${e.id}/company/systems`,async route=>{if(!oldSourceOnce)return route.fallback();oldSourceOnce=false;oldSourcesRequested();await oldSourcesWait;return route.fulfill({contentType:'application/json',body:JSON.stringify({systems:[],registry_sha256:'f'.repeat(64)})});});
  await page.getByRole('button',{name:"Load participant's source systems",exact:true}).click();await oldSourcesSeen;
  await page.getByLabel('Ask the owner').fill('Question retained across participant switch');
  await page.getByRole('button',{name:/Other participant meeting/}).click();
  if(await page.getByLabel('Ask the owner').inputValue()!=='Question retained across participant switch')throw Error('Meeting switch lost question');
  await page.getByRole('button',{name:/Infrastructure walkthrough/}).click();
  await page.getByText('Choose exact company records for this question',{exact:true}).click();
  await page.getByText('0 explicit source records selected',{exact:true}).waitFor();
  await page.getByRole('button',{name:"Load participant's source systems",exact:true}).click();
  await page.getByLabel('Participant source system',{exact:true}).selectOption('owned:SYS');
  await page.getByRole('button',{name:'Load source records',exact:true}).click();
  await page.getByRole('button',{name:'Use record REC-1 version 1',exact:true}).click();
  releaseOldSources();await page.waitForTimeout(100);await page.getByRole('button',{name:'Remove source REC-1',exact:true}).waitFor();
  await page.getByLabel('Ask the owner').fill('First queued question');
  await page.getByRole('button',{name:'Send message',exact:true}).click();await sent;
  await page.getByLabel('Ask the owner').fill('Next question typed during acceptance');
  await page.getByRole('button',{name:'Remove source REC-1',exact:true}).click();
  await page.getByRole('button',{name:'Use record REC-2 version 2',exact:true}).click();
  acceptQueued();
  await page.waitForTimeout(150);
  if(await page.getByLabel('Ask the owner').inputValue()!=='Next question typed during acceptance')throw Error('Delayed acceptance cleared newer meeting draft');
  if(submittedEnvelope.payload.content!=='First queued question'||!submittedEnvelope.command_id)throw Error('Background submission changed original envelope');
  if(submittedEnvelope.payload.source_records?.[0]?.record_id!=='REC-1'||submittedEnvelope.payload.source_records[0].system_id!=='owned:SYS')throw Error('Exact selected pin not retained in command');
  await page.getByRole('button',{name:'Remove source REC-2',exact:true}).waitFor();
  let lostEnvelope=null,retriedEnvelope=null,dropSourcePost=true;
  await page.route(`**/api/engagements/${e.id}/jobs`,async route=>{
    if(route.request().method()!=='POST')return route.fallback();
    const value=route.request().postDataJSON();
    if(dropSourcePost){dropSourcePost=false;lostEnvelope=value;return route.abort('failed');}
    retriedEnvelope=value;return route.fulfill({contentType:'application/json',body:JSON.stringify({...backgroundJob,status:'PENDING'})});
  });
  await page.getByRole('button',{name:'Send message',exact:true}).click();
  await page.getByRole('button',{name:'Restore unconfirmed question',exact:true}).waitFor();
  await page.getByLabel('Ask the owner').fill('Newer unsent question must survive restore');
  await page.getByRole('button',{name:'Restore unconfirmed question',exact:true}).click();
  if(await page.getByLabel('Ask the owner').inputValue()!=='Newer unsent question must survive restore')throw Error('Restore overwrote newer composer');
  await page.getByLabel('Ask the owner').fill('');await page.getByRole('button',{name:'Remove source REC-2',exact:true}).click();
  await page.getByRole('button',{name:'Restore unconfirmed question',exact:true}).click();
  await page.getByRole('button',{name:'Remove source REC-2',exact:true}).waitFor();
  await page.getByRole('button',{name:'Send message',exact:true}).click();await page.waitForTimeout(150);
  if(JSON.stringify(lostEnvelope)!==JSON.stringify(retriedEnvelope))throw Error('Transport retry changed exact source envelope');
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
  boundFixture.snapshot.snapshot_isolation='PER_COMPONENT_NOT_GLOBAL';
  boundFixture.snapshot.sources=[{id:'BOUND-S1',company:'NEUTRAL_COMPANY',branch:'NEUTRAL_BRANCH',system:'NATIVE_SYS',record:'NATIVE_RECORD',version:3,sha256:'1'.repeat(64),source_store_id:'neutral-original-store',source_system_alias:'neutral:NATIVE_SYS',registry_sha256:'2'.repeat(64),event_at:null,available_at:'2027-01-01T00:00:00Z',imported_at:'2027-01-02T00:00:00Z',actor_granted_at_binding:false,actor_visibility_at_binding:'ACCESS_NOT_GRANTED',retained_audit_artifact_ids:['ART-NEUTRAL'],fact_verification:'Native identity and retained digest checked; interpretation unvalidated.'}];
  e.artifacts.push({id:'ART-NEUTRAL',name:'Neutral bound original.json',status:'AVAILABLE',engagement_id:e.id,sha256:'1'.repeat(64),version:1,source:{kind:'COLLECTED_COMPANY_SOURCE',receipt:{engagement_id:e.id,source:{company:'NEUTRAL_COMPANY',branch:'NEUTRAL_BRANCH',system:'NATIVE_SYS',record:'NATIVE_RECORD',version:3,sha256:'1'.repeat(64),source_store_id:'neutral-original-store',source_system_alias:'neutral:NATIVE_SYS',registry_sha256:'2'.repeat(64)}}}});
  boundFixture.snapshot.authored.issues[0].source_ids=['BOUND-S1'];
  boundFixture.snapshot.authored.expectations[0].task_ids=['T-01'];
  boundFixture.snapshot.authored.expectations.push({id:'E-LEGACY',issue_ids:['I1'],procedure:'Legacy expectation without a procedure mapping',acceptable_alternatives:[]});
  let comparisonMode='normal';let requestedHistory;let boundRouteCalls=0;let delayComparison=true,releaseComparison;

  await page.route(`**/api/engagements/${e.id}/instructor-binding`,route=>{boundRouteCalls++;return route.fulfill({contentType:'application/json',body:JSON.stringify(boundFixture)});} );
  await page.route(`**/api/engagements/${e.id}/instructor-comparison?*`,async route=>{
    requestedHistory=Number(new URL(route.request().url()).searchParams.get('revision'));
    const value={status:comparisonMode==='mismatch'?'CONTEXT_MISMATCH':'DETERMINISTIC_LINK_INVENTORY_ONLY',engagement_id:e.id,audited_actor_id:'LEARNER-NEUTRAL',binding_manifest_sha256:(comparisonMode==='changed'?'f':'d').repeat(64),bound_revision:0,selected_history_revision:requestedHistory,current_revision:e.revision,selected_state_sha256:'a'.repeat(64),selected_history_sha256:'b'.repeat(64),selected_history_tip_sha256:'c'.repeat(64),grading:'NOT_PERFORMED',professional_validation:'UNVALIDATED',mismatches:comparisonMode==='mismatch'?['CURRENT_COMPANY_BASIS_DIFFERS_FROM_BOUND_SOURCE']:[],limits:['No inspection or sufficiency determination'],sources:[],audited_actor_activity:[{revision:1,command_id:'NEUTRAL1',kind:'note.create'}],shared_workspace_activity_count:2,expectations:[{expectation_id:'E1',status:'NO_EXPLICIT_WORKPAPER_SOURCE_LINK_RECORDED',source_linked_workpaper_versions:[],workpaper_version_reviews:[],source_linked_populations:[],population_linked_selections:[],control_associated_records_only:{requests:[],tasks:[{id:'T-01',recorded_status:'COMPLETE'}]}}]};
    value.expectations[0].authored_task_ids=['T-01'];value.expectations[0].task_mapping_status='EXPLICIT_AUTHORED_LINKS';
    value.expectations[0].task_linked_workpaper_versions=[{id:'WP-TASK-LINKED',version:1,version_sha256:'3'.repeat(64),task_ids:['T-01'],source_artifact_ids:[]}];
    value.expectations.push({expectation_id:'E-LEGACY',status:'NO_EXPLICIT_WORKPAPER_SOURCE_LINK_RECORDED',source_linked_workpaper_versions:[],workpaper_version_reviews:[],source_linked_populations:[],population_linked_selections:[],control_associated_records_only:{requests:[],tasks:[]}});
    if(delayComparison){delayComparison=false;await new Promise(resolve=>{releaseComparison=resolve;});}
    return route.fulfill({contentType:'application/json',body:JSON.stringify(value)});
  });
  // Newer shared version deliberately has no task link; the protected DTO keeps v1 only.
  e.workpapers.push({id:'WP-TASK-LINKED',title:'Neutral authored procedure work',versions:[{id:'TASK-WPV1',version:1,task_ids:['T-01'],evidence_ids:[],text:'Historical explicitly linked version'},{id:'TASK-WPV2',version:2,task_ids:[],evidence_ids:[],text:'Newer unlinked version must not substitute'}]});
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=review`);
  await page.getByRole('region',{name:'Authored issue index',exact:true}).getByRole('button').first().click();
  await page.getByRole('region',{name:'Selected authored issue',exact:true}).getByText('E1',{exact:true}).click();
  await page.getByLabel('Find bound source',{exact:true}).fill('neutral:NATIVE_SYS');
  await page.getByText('1 of 1 originals match this scope and search',{exact:false}).waitFor();
  await page.getByRole('button',{name:'BOUND-S1 · NATIVE_RECORD · v3',exact:true}).click();
  const boundSource=page.getByRole('article',{name:'Selected bound source',exact:true});
  await boundSource.getByText('neutral-original-store',{exact:true}).waitFor();await boundSource.getByText('neutral:NATIVE_SYS',{exact:true}).waitFor();await boundSource.getByText('2'.repeat(64),{exact:true}).waitFor();await boundSource.getByText(/NEUTRAL_COMPANY \/ NEUTRAL_BRANCH \/ NATIVE_SYS/).waitFor();await boundSource.getByText(/no shared transaction across the portfolio/).waitFor();
  const boundCopy=page.getByRole('button',{name:'Inspect retained original ART-NEUTRAL',exact:true});await boundCopy.click();await page.getByRole('dialog').getByRole('heading',{name:'Neutral bound original.json',exact:true}).waitFor();await page.getByRole('dialog').getByRole('button',{name:'Back to bound source',exact:true}).click();
  if(await page.getByLabel('Find bound source',{exact:true}).inputValue()!=='neutral:NATIVE_SYS')throw Error('Retained-original preview lost bound search');await boundSource.getByText('neutral-original-store',{exact:true}).waitFor();if(!await boundCopy.evaluate(el=>el===document.activeElement))throw Error('Bound preview Back did not restore source button focus');
  await page.getByText(/Explicit authored procedure IDs: T-01/).waitFor();

  await page.getByText('Trace recorded work against bound expectations',{exact:true}).click();
  const comparison=page.locator('.instructor-comparison');
  await comparison.getByLabel('History revision',{exact:true}).fill('1');
  await comparison.getByRole('button',{name:'Trace recorded links',exact:true}).click();
  await comparison.getByRole('status').filter({hasText:'Reading and verifying the selected history'}).waitFor();
  await page.getByRole('button',{name:/PBC & evidence/}).click();
  if(await comparison.isVisible())throw Error('Inactive retained key stayed visible');
  await page.getByRole('button',{name:/Workpapers & review/}).click();
  if(await page.getByLabel('Find bound source',{exact:true}).inputValue()!=='neutral:NATIVE_SYS')throw Error('Panel switch erased bound search');
  await comparison.getByRole('status').waitFor();if(!releaseComparison)throw Error('Pending comparison not retained');releaseComparison();
  await comparison.getByText(/1 recorded commands by the audited actor.*2 by other actors/).waitFor();
  if(requestedHistory!==1)throw Error('Comparison silently selected current history');
  await comparison.getByLabel('Bound expectation',{exact:true}).selectOption('E1');
  await comparison.getByText(/This does not establish a missed issue/).waitFor();
  await comparison.getByText(/Control-associated procedures · 1/).click();
  await comparison.getByText('T-01',{exact:true}).waitFor();
  await comparison.getByText(/The author explicitly linked this expectation/).waitFor();
  await comparison.getByText('Workpaper versions with explicit procedure links · 1',{exact:true}).click();
  const taskVersionDetails=comparison.locator('details').filter({has:page.getByText('Workpaper versions with explicit procedure links · 1',{exact:true})});
  await taskVersionDetails.getByText('WP-TASK-LINKED',{exact:true}).waitFor();await taskVersionDetails.getByText(/version 1/).waitFor();
  if(await taskVersionDetails.getByText(/version 2/).count())throw Error('Authored task comparison substituted newer unlinked workpaper');
  const emptyIntersection=taskVersionDetails.locator('div').filter({has:page.locator('dt').getByText('source artifact ids',{exact:true})});await emptyIntersection.locator('dd').getByText('[]',{exact:true}).waitFor();
  await comparison.getByLabel('Bound expectation',{exact:true}).selectOption('E-LEGACY');await comparison.getByText(/has no explicit procedure mapping in this report/).waitFor();await comparison.getByText('Workpaper versions with explicit procedure links · 0',{exact:true}).waitFor();
  comparisonMode='mismatch';
  await comparison.getByRole('button',{name:'Trace recorded links',exact:true}).click();
  await comparison.getByText(/Record comparison is withheld/).waitFor();
  if(await comparison.getByLabel('Bound expectation',{exact:true}).count())throw Error('Mismatch exposed expectation comparison');
  comparisonMode='changed';
  await comparison.getByRole('button',{name:'Trace recorded links',exact:true}).click();
  await comparison.getByRole('alert').waitFor();
  if(await comparison.getByText(/recorded commands by the audited actor/).count())throw Error('Changed manifest retained comparison');
  delete boundFixture.snapshot.sources[0].registry_sha256;
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=review`);await page.getByRole('alert').filter({hasText:'Protected source routing pins are incomplete.'}).waitFor();
  if(await page.getByRole('button',{name:'BOUND-S1 · NATIVE_RECORD · v3',exact:true}).count())throw Error('Incomplete portfolio route exposed bound source');
  boundFixture.snapshot.sources[0].registry_sha256='2'.repeat(64);
  e.permissions=['learn'];const protectedCalls=boundRouteCalls;
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=review`);await page.getByLabel('Current engagement context').waitFor();await page.waitForTimeout(100);
  if(boundRouteCalls!==protectedCalls||await page.getByText('neutral-original-store',{exact:true}).count()||await page.locator('.instructor-comparison').count())throw Error('Learner exposed protected bound key route or DOM');
  e.permissions=['instruct','review','learn'];

  e.capabilities.company_sources=true;e.capabilities.company_source_impact=false;e.capabilities.company_populations=false;
  let portfolioCollected=null,portfolioPagePin=null,releaseSourceIndex;let delaySourceIndex=true;const sourceIndexResolvers=[];
  const alias='ledger:SOURCE_SYS',registry='e'.repeat(64);
  await page.route(`**/api/engagements/${e.id}/company/systems`,async route=>{if(delaySourceIndex){await new Promise(resolve=>{sourceIndexResolvers.push(resolve);releaseSourceIndex=()=>{delaySourceIndex=false;sourceIndexResolvers.forEach(done=>done());};});}return route.fulfill({contentType:'application/json',body:JSON.stringify({systems:[{system:alias,owner:'P-01',source_store_id:'documentary',portfolio_qualification:'QUALIFIED_SOURCE_PORTFOLIO_NOT_COHERENT_OPERATING_YEAR'}],registry_sha256:registry,snapshot_isolation:'PER_SOURCE_NOT_GLOBAL'})});});
  await page.route(`**/api/engagements/${e.id}/company/systems/*/records?*`,route=>route.fulfill({contentType:'application/json',body:JSON.stringify({records:[{company:'ORIGINAL_COMPANY',branch:'ORIGINAL_BRANCH',system:'SOURCE_SYS',record:'NATIVE_RECORD',version:4,sha256:'a'.repeat(64),source_store_id:'documentary',source_system_alias:alias,registry_sha256:registry,provenance:{name:'/private/source-store/native-original.csv'},event_at:null,available_at:'2027-01-01T00:00:00Z'}],next_after_record:null,registry_sha256:portfolioPagePin??registry,snapshot_isolation:'ONE_SOURCE_PAGE_ONLY'})}));
  await page.route(`**/api/engagements/${e.id}/commands`,route=>{const c=route.request().postDataJSON();if(c.kind!=='company.collect')return route.fallback();portfolioCollected=c.payload;return route.fulfill({contentType:'application/json',body:JSON.stringify(e)});});
  const privateReadsBeforePbc=boundRouteCalls;
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=pbc`);
  await page.getByText('Browse company source records',{exact:true}).click();
  await page.getByRole('status').filter({hasText:'Loading company source systems'}).waitFor();if(boundRouteCalls!==privateReadsBeforePbc)throw Error('Hidden unvisited bound key fetched private content');if(await page.getByLabel('Company system',{exact:true}).isEnabled())throw Error('Pending source selector enabled');if(await page.getByText('No company systems are available through this engagement connection.',{exact:true}).count())throw Error('Loading index reported an empty system census');if(!releaseSourceIndex)throw Error('No pending source index');releaseSourceIndex();
  await page.getByLabel('Company system',{exact:true}).selectOption(alias);
  await page.getByText('Original filename: native-original.csv',{exact:true}).waitFor();
  if((await page.locator('body').innerText()).includes('/private/source-store'))throw Error('Source filename leaked a filesystem path');
  await page.getByText(/ORIGINAL_COMPANY \/ ORIGINAL_BRANCH \/ SOURCE_SYS \/ NATIVE_RECORD/).waitFor();
  await page.getByText(/Page received by browser:/).waitFor();
  await page.getByText(/not a coherent operating year or a single synchronized snapshot/).waitFor();
  if(await page.getByText('Check collected sources for changes',{exact:true}).count())throw Error('Unsupported portfolio impact panel shown');
  await page.getByLabel('Link collection to request',{exact:true}).selectOption('PBC-01');
  await page.getByRole('button',{name:/Populations & samples/}).click();await page.getByRole('button',{name:/PBC & evidence/}).click();
  if(await page.getByLabel('Company system',{exact:true}).inputValue()!==alias||await page.getByLabel('Link collection to request',{exact:true}).inputValue()!=='PBC-01')throw Error('Panel switch lost source collection context');await page.getByText('Original filename: native-original.csv',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Collect this version',exact:true}).click();
  await page.waitForTimeout(100);
  if(portfolioCollected?.system_id!==alias||portfolioCollected?.record_id!=='NATIVE_RECORD'||portfolioCollected?.version!==4)throw Error('Portfolio collection replaced alias with native system');
  portfolioPagePin='f'.repeat(64);
  await page.getByLabel('Company system',{exact:true}).selectOption('');
  await page.getByLabel('Company system',{exact:true}).selectOption(alias);
  await page.getByRole('alert').filter({hasText:'Source portfolio identity changed'}).waitFor();
  if(await page.getByRole('button',{name:'Collect this version',exact:true}).count())throw Error('Changed registry retained collectible records');
  await page.getByRole('button',{name:/Populations & samples/}).click();
  if(await page.getByText('Collect a company source population',{exact:true}).count())throw Error('Unsupported portfolio population collector shown');
  e.capabilities.company_source_impact=true;e.artifacts[0].sha256='a'.repeat(64);
  let impactMode='current',releaseImpact;
  await page.route(`**/api/engagements/${e.id}/company/impact`,async route=>{
    const report={status:'OBSERVABLE_SOURCE_CHANGE_REVIEW',engagement_id:e.id,engagement_revision:impactMode==='stale'?e.revision-1:e.revision,simulated_as_of:e.simulated_at,started_at:'2026-09-14T20:00:00Z',completed_at:'2026-09-14T20:00:01Z',compared_artifacts:2,unavailable_comparisons:3,snapshot_isolation:'PER_SOURCE_OPERATION_NOT_GLOBAL',changes:[{artifact_id:e.artifacts[0].id,collected_version:1,latest_visible_version:2,collected_sha256:'a'.repeat(64),latest_visible_sha256:'b'.repeat(64),source_identity:{company:'ORIGINAL_COMPANY',branch:'B',system:'SYS',record:'R',source_store_id:'original-store',source_system_alias:'portfolio:SYS',registry_sha256:'e'.repeat(64)},latest_source_qualifiers:{record_status:'WITHDRAWN'},discovered_at:'2026-09-14T20:00:00Z',rechecked_at:'2026-09-14T20:00:01Z',references:[]}]};
    if(impactMode==='delayed')await new Promise(r=>{releaseImpact=r;});
    return route.fulfill({contentType:'application/json',body:JSON.stringify(report)});
  });
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=pbc`);
  await page.getByText('Check collected sources for changes',{exact:true}).click();
  await page.getByRole('button',{name:'Check source changes',exact:true}).click();
  await page.getByText(/2 retained artifacts compared · 1 later source versions observed · 3 comparisons unavailable/).waitFor();
  await page.getByText(/record_status: WITHDRAWN/).waitFor();await page.getByText(/Collection route: portfolio:SYS/).waitFor();
  await page.getByRole('button',{name:'Open artifact '+e.artifacts[0].id,exact:true}).click();await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');
  impactMode='stale';await page.getByRole('button',{name:'Check source changes',exact:true}).click();await page.getByRole('alert').filter({hasText:'Source comparison is outdated'}).waitFor();
  if(await page.getByText(/record_status: WITHDRAWN/).count())throw Error('Stale impact retained previous result');
  impactMode='delayed';await page.getByRole('button',{name:'Check source changes',exact:true}).click();await page.waitForTimeout(100);await page.getByRole('button',{name:/Notes/}).first().click();releaseImpact();await page.waitForTimeout(100);await page.getByRole('button',{name:/PBC & evidence/}).click();
  if(await page.getByText(/record_status: WITHDRAWN/).count())throw Error('Late impact response crossed section lifetime');
  e.artifacts[0].status='AVAILABLE';e.artifacts[0].source={kind:'COLLECTED_COMPANY_SOURCE',receipt:{engagement_id:e.id,source:{system:'SYS',source_system_alias:'conversation:SYS',record:'SAVED-R',version:2,sha256:e.artifacts[0].sha256}}};
  e.meetings[0].messages.push({id:'SAVED-USER',role:'user',content:'Neutral saved source question',source_records:[{system_id:'conversation:SYS',record_id:'SAVED-R',version:2,sha256:e.artifacts[0].sha256}]});
  e.meetings[0].messages.push({id:'SAVED-REPLY',role:'assistant',content:'Neutral response with retained action receipt',source_refs:['SOURCE-SNAPSHOT-NEUTRAL'],action_receipts:[{kind:'pbc.followup',executed:true,status:'ACKNOWLEDGED',authority:'SCOPED_ENGINE_COMMAND',request_id:'PBC-01',reason:'Neutral recorded source follow-up'},{kind:'pbc.create',executed:false,status:'REJECTED',authority:'SCOPED_ENGINE_COMMAND',request_id:'MISSING'}]});
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=meetings`);
  await page.getByRole('button',{name:/Infrastructure walkthrough/}).click();
  await page.getByText('Exact source records selected for this question (1)',{exact:true}).click();
  await page.getByText(/conversation:SYS \/ SAVED-R · Version 2/).waitFor();
  await page.getByRole('button',{name:'Open retained original '+e.artifacts[0].id,exact:true}).click();await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');
  await page.getByText('Source references recorded with this reply (1)',{exact:true}).click();await page.getByText('SOURCE-SNAPSHOT-NEUTRAL',{exact:true}).waitFor();
  await page.getByText('Executed scoped action: pbc.followup · ACKNOWLEDGED',{exact:true}).waitFor();await page.getByText('Action not executed: pbc.create · REJECTED',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Open affected request PBC-01',exact:true}).click();await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');
  e.capabilities.company_source_census=true;e.background_command_kinds=['meeting.message','company.census.collect'];e.requests[0].boundary_id=e.scope.boundaries[0];e.phase='ACTIVE';
  let censusEnvelope=null,censusImport=null;
  const censusJob={...backgroundJob,id:'JOB-CENSUS',kind:'company.census.collect',status:'PENDING',expected_revision:e.revision,result_revision:null};
  await page.route(`**/api/engagements/${e.id}/company/systems`,route=>route.fulfill({contentType:'application/json',body:JSON.stringify({systems:[{system:'CENSUS:SYS',owner:'P-01',source_store_id:'census-original'}]})}));
  await page.route(`**/api/engagements/${e.id}/jobs`,route=>{if(route.request().method()==='POST'){censusEnvelope=route.request().postDataJSON();return route.fulfill({contentType:'application/json',body:JSON.stringify(censusJob)});}return route.fulfill({contentType:'application/json',body:JSON.stringify({jobs:censusEnvelope?[censusJob]:[]})});});
  await page.route(`**/api/engagements/${e.id}/jobs/JOB-CENSUS/input`,route=>route.fulfill({contentType:'application/json',body:JSON.stringify(censusEnvelope)}));
  await page.route(`**/api/engagements/${e.id}/commands`,route=>{const c=route.request().postDataJSON();if(c.kind!=='population.import')return route.fallback();censusImport=c;return route.fulfill({contentType:'application/json',body:JSON.stringify(e)});});
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=populations`);await page.getByText('Collect a source-record census',{exact:true}).click();
  await page.getByRole('button',{name:'Load census source systems',exact:true}).click();await page.getByLabel('Census source system',{exact:true}).selectOption('CENSUS:SYS');await page.getByLabel('Census version policy',{exact:true}).selectOption('LATEST_VISIBLE_PER_RECORD');await page.getByLabel('Census event window start',{exact:true}).fill('2027-01-01T00:00:00Z');await page.getByLabel('Census event window end',{exact:true}).fill('2028-01-01T00:00:00Z');await page.getByLabel('Census undated policy',{exact:true}).selectOption('INCLUDE_UNDATED_STRATUM');await page.getByLabel('Census evidence request',{exact:true}).selectOption('PBC-01');
  await page.getByRole('button',{name:/Notes/}).first().click();await page.getByRole('button',{name:/Populations & samples/}).click();if(await page.getByLabel('Census source system',{exact:true}).inputValue()!=='CENSUS:SYS')throw Error('Census query lost across navigation');
  await page.getByRole('button',{name:'Collect census and source manifest',exact:true}).click();await page.getByRole('status').filter({hasText:'Census submission accepted (initial status: pending)'}).waitFor();if(censusEnvelope?.kind!=='company.census.collect'||censusEnvelope.payload.system_id!=='CENSUS:SYS'||censusEnvelope.payload.query.unknown_event_policy!=='INCLUDE_UNDATED_STRATUM')throw Error('Wrong census envelope');if(censusImport)throw Error('Census automatically imported');
  await page.getByText('Company replies and background work',{exact:true}).click();await page.getByRole('button',{name:'Inspect queued census query',exact:true}).click();await page.getByText(/Source-record census · System CENSUS:SYS · Request PBC-01/).waitFor();
  const censusNext={kind:'population.import',payload:{title:'Explicit source census',artifact_id:'CENSUS-ROWS',rows:[{id:'SV1',date_stratum:'IN_EVENT_WINDOW'},{id:'SV2',date_stratum:'UNDATED'}],scope:{unit:'SOURCE_RECORD_VERSION'},source:{query_manifest_sha256:'f'.repeat(64)}}};
  e.requests[0].company_census_collections=[{snapshot_id:'SNAP-CENSUS',manifest_sha256:'f'.repeat(64),query:censusEnvelope.payload.query,system_id:'CENSUS:SYS',source_versions:2,distinct_source_records:2,strata:{IN_EVENT_WINDOW:1,UNDATED:1},excluded:{outside_event_window:2,undated:0},native_artifacts:[1,2].map(n=>({artifact_id:'CENSUS-ORIG-'+n,source:{company:'ORIGINAL',branch:'B',system:'SYS',record:'R'+n,version:1,sha256:String(n).repeat(64),origin:'LOCAL_SYNTHETIC',date_stratum:n===1?'IN_EVENT_WINDOW':'UNDATED'}})),manifest_artifact_id:'CENSUS-MANIFEST',population_artifact_id:'CENSUS-ROWS',next_command:censusNext,registration:'AWAITING_EXPLICIT_IMPORT',recorded_at:'2026-09-14T20:00:00Z',simulated_at:e.simulated_at}];e.revision++;censusJob.status='COMPLETED';censusJob.result_revision=e.revision;
  await page.getByText('CENSUS:SYS · 2 source versions · 2 distinct source records',{exact:true}).waitFor();await page.getByText(/In event window: 1 · Undated: 1/).waitFor();const importCensus=page.getByRole('button',{name:'Import reviewed census as provisional',exact:true});if(await importCensus.isEnabled())throw Error('Census import enabled before explicit review');await page.getByRole('checkbox',{name:'I reviewed the exact query, version unit, undated stratum and source qualifiers for provisional import.',exact:true}).check();await importCensus.click();await page.waitForTimeout(100);if(JSON.stringify(censusImport?.payload)!==JSON.stringify(censusNext.payload))throw Error('Provisional import changed exact census rows or pins');
  e.artifacts.push({id:'LINEAGE-MANIFEST',name:'Neutral query manifest',status:'AVAILABLE',sha256:'b'.repeat(64)});
  const lineagePop={id:'POP-LINEAGE',title:'Neutral exact source population',version:1,count:4,status:'PROVISIONAL',artifact_id:e.artifacts[0].id,immutable:{source_json:JSON.stringify({original_sha256:e.artifacts[0].sha256,query_manifest_artifact_id:'LINEAGE-MANIFEST',query_manifest_sha256:'b'.repeat(64)})}};
  e.populations.push(lineagePop);e.selections.push({id:'SEL-LINEAGE',population_id:'POP-LINEAGE',population_version:1,selected_ids:['R1'],method:'manual',purpose:'Neutral selected item inspection'},{id:'SEL-UNAVAILABLE',population_id:'POP-LINEAGE',population_version:99,selected_ids:['R1'],method:'manual',purpose:'Unavailable exact version'});
  e.workpapers.push({id:'WP-LINEAGE',title:'Neutral linked workpaper',versions:[{id:'LV1',version:1,actor:'OTHER',text:'Exact first-version work',evidence_ids:[e.artifacts[0].id]},{id:'LV2',version:2,actor:'OTHER',text:'Later version not explicitly linked',evidence_ids:[]}]});
  await page.goto(`http://127.0.0.1:5193/?engagement=${e.id}&view=meetings`);await page.getByLabel('Ask the owner').fill('Keep this investigation question while tracing evidence');await page.getByRole('button',{name:/Populations & samples/}).click();
  const selectionsTable=page.locator('.record-table').filter({has:page.getByRole('button',{name:'Sort by Selection',exact:true})});await selectionsTable.getByRole('searchbox').fill('SEL-LINEAGE');await selectionsTable.getByRole('button',{name:'SEL-LINEAGE',exact:true}).click();
  let lineageDialog=page.getByRole('dialog');await lineageDialog.getByRole('button',{name:'Open population POP-LINEAGE version 1',exact:true}).click();await lineageDialog.getByRole('button',{name:'Open pinned query manifest LINEAGE-MANIFEST',exact:true}).click();await lineageDialog.getByRole('button',{name:'Back to population POP-LINEAGE',exact:true}).click();await lineageDialog.getByRole('button',{name:'Open workpaper WP-LINEAGE version 1',exact:true}).click();
  await lineageDialog.getByText('Showing explicitly linked workpaper version 1. Other versions are not substituted.',{exact:true}).waitFor();const versionsTable=lineageDialog.locator('.record-table');await versionsTable.getByText('Exact first-version work',{exact:true}).waitFor();if(await versionsTable.getByText('Later version not explicitly linked',{exact:true}).count())throw Error('Lineage substituted a newer workpaper version');
  await lineageDialog.getByRole('button',{name:'Back to population POP-LINEAGE',exact:true}).click();await lineageDialog.getByRole('button',{name:'Back to selection SEL-LINEAGE',exact:true}).click();await page.keyboard.press('Escape');if(await selectionsTable.getByRole('searchbox').inputValue()!=='SEL-LINEAGE')throw Error('Lineage lost initiating selection filter');
  await selectionsTable.getByRole('searchbox').fill('SEL-UNAVAILABLE');await selectionsTable.getByRole('button',{name:'SEL-UNAVAILABLE',exact:true}).click();await page.getByRole('dialog').getByText(/exact population POP-LINEAGE version 99 is unavailable/).waitFor();if(await page.getByRole('dialog').getByRole('button',{name:'Open population POP-LINEAGE version 1',exact:true}).count())throw Error('Missing historical population silently rebased');await page.keyboard.press('Escape');await page.getByRole('button',{name:/Meetings · MRL/}).click();if(await page.getByLabel('Ask the owner').inputValue()!=='Keep this investigation question while tracing evidence')throw Error('Lineage navigation erased current question');
  if (errors.length) throw Error(errors.join("\n"));
  await writeFile(
    `${output}/browser-receipt.json`,
    JSON.stringify(
      {
        fixture:
          "Public synthetic layout data; API mocked; not a backend acceptance claim",
        views: 10,
        lineage_checks:['selection to exact population source manifest and workpaper version','nested return retains original selection filter','newer workpaper version not substituted','missing historical population fails closed','current investigation question preserved'],
        census_checks:['query preserved across section navigation','exact background census envelope','pending acceptance not complete population','queued query inspection distinguishes census from meeting','dated/undated/excluded counts distinct','no automatic import; explicit provisional command preserves rows and manifest pin'],
        saved_conversation_checks:['exact historical source pins visible and original preview','source snapshot citation ID preserved','executed action distinguished from unexecuted proposal','affected request preview exact'],
        source_impact_checks:['compared and unavailable denominators distinct','original and alias source identity','source withdrawal qualifier is not audit conclusion','exact retained original preview','outdated response removes prior result','late response cannot cross component lifetime'],
        meeting_source_checks:['only participant-owned systems','meeting switch clears pins without losing question','late source response cannot clear new meeting selection','exact alias/version/SHA command pins','delayed acceptance preserves newer selection and question','queued retry inspection shows original pins','ambiguous transport retry preserves exact envelope','restore refuses overwrite of newer composer'],
        portfolio_checks:['originalsixpartidentity distinct from route alias','originalfilename preserved without filesystem path','registry pin change removes collectible records','registry pin/perpage receipt qualification','collection uses exact selectedalias','unsupported impact/population panels absent'],
        comparison_checks:['pending comparison and key search survive panel switch','source system/request/loaded page survive panel switch','source index loading is announced without premature empty claim','exact retained bound original opens existing preview and Back preserves key search/selection/focus','bound source search matches alias absent from native identity','full native/store/alias/registry identity displayed','explicit authored task historical WPv1 with empty source intersection','newer unlinked WPv2 not substituted','legacy unmapped expectation supported','incomplete portfolio route rejected','learner bound route and DOM withheld','explicit historical revision preserved','audited vs shared commands distinct','missing link not missedissue inference','context mismatch withholds all comparisons','changed bound manifest rejected'],
        work_status_checks:['exact denominators retain exclusions','selected control procedure and source previews','outdated revision clears previous report','late response after section exit discarded','no status panel without current engagement permissions'],
        investigation_checks:['explicit user question/link save and reload','current pinned record preview','409 retains unsaved editor without overwrite','changed source pin non-clickable','dirty editor prevents silent investigation switch','changed branch/acquisition/permission basis blocks exact pin until explicit review/save'],
        background_checks: ['pending navigation and reload continuity','no eager queued input reads','explicit exact question inspection gates retry','observed job revision retained','conflicted job never retries','delayed acceptance preserves newly typed next question'],
        procedure_link_checks:["explicit same-control procedure added to version draft","procedure and control survive reopen","explicit procedure removal"],
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
