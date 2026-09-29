// Synthetic authorized projections only. Run after npm run build; no live API calls.
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
const output = resolve(
  "../enterprise/generated/audit-suite/build/accessibility",
);
await mkdir(output, { recursive: true });
const server = spawn(
  process.execPath,
  [
    "node_modules/vite/bin/vite.js",
    "preview",
    "--host",
    "127.0.0.1",
    "--port",
    "5198",
    "--strictPort",
  ],
  { stdio: "ignore" },
);
let browser;
const measurements = [];
try {
  for (let i = 0; i < 50; i++) {
    try {
      if ((await fetch("http://127.0.0.1:5198")).ok) break;
    } catch {}
    await new Promise((r) => setTimeout(r, 100));
  }
  browser = await chromium.launch({
    executablePath: "/usr/bin/chromium",
    headless: true,
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1050 },
  });
  page.setDefaultTimeout(8000);
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
          {
            role_ref: "Neutral owner",
            beliefs: ["Authored statement only"],
            knows_fact_ids: ["F1"],
          },
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
          {
            id: "actor:0",
            kind: "actor",
            source_pointer: "/actor_knowledge/0",
          },
          { id: "event:E1", kind: "event", source_pointer: "/events/0" },
          { id: "path:P1", kind: "path", source_pointer: "/playable_paths/0" },
        ],
        edges: [
          {
            from: "actor:0",
            to: "fact:F1",
            relation: "AUTHORED_KNOWLEDGE",
            source_pointer: "/actor_knowledge/0/knows_fact_ids/0",
          },
        ],
        edge_semantics: "AUTHORED_REFERENCES_ONLY_NOT_CORROBORATION",
      },
    },
  };

  e.capabilities.personal_drafts = false;
  let commands = 0;
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/commands")) {
      commands++;
      return route.fulfill({
        status: 409,
        json: { error: "Synthetic stale revision: refresh before saving" },
      });
    }
    let body = e;
    if (path === "/api/bootstrap")
      body = {
        viewer: {
          id: "fixture",
          display_name: "Synthetic reviewer",
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
      };
    else if (path.includes("/instructor-key"))
      body = path.endsWith("/instructor-key") ? keyIndex : keyDetail;
    else if (path.includes("/drafts/"))
      body = { status: "EMPTY", version: 0, fields: {} };
    return route.fulfill({ status: 200, json: body });
  });
  async function tabTo(locator, max = 160) {
    for (let i = 0; i < max; i++) {
      if (await locator.evaluate((el) => el === document.activeElement)) return;
      await page.keyboard.press("Tab");
    }
    throw Error(
      "Keyboard could not reach " +
        (await locator.getAttribute("aria-label")) +
        " " +
        (await locator.textContent()),
    );
  }
  async function enter(locator) {
    await tabTo(locator);
    await page.keyboard.press("Enter");
  }
  async function contrast(locator, label, focus = false) {
    const result = await locator.evaluate((el, focus) => {
      const rgb = (s) => s.match(/[\d.]+/g).map(Number);
      const lum = (c) =>
        c
          .slice(0, 3)
          .map((x) => {
            x /= 255;
            return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
          })
          .reduce((a, x, i) => a + x * [0.2126, 0.7152, 0.0722][i], 0);
      const style = getComputedStyle(el);
      let parent = focus ? el.parentElement : el,
        bg;
      while (parent) {
        bg = rgb(getComputedStyle(parent).backgroundColor);
        if (bg.length < 4 || bg[3] === 1) break;
        if (bg[3] !== 0)
          throw Error("Translucent background needs explicit compositing");
        parent = parent.parentElement;
      }
      const color = focus ? style.outlineColor : style.color,
        fg = rgb(color);
      if (fg[3] !== undefined && fg[3] !== 1)
        throw Error("Translucent foreground");
      const a = lum(fg),
        b = lum(bg || [255, 255, 255]);
      return {
        ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05),
        color,
        background: bg,
        outline: style.outlineStyle,
        width: style.outlineWidth,
        focusVisible: el.matches(":focus-visible"),
      };
    }, focus);
    measurements.push({ label, ...result });
    if (result.ratio < (focus ? 3 : 4.5))
      throw Error(`${label} contrast ${result.ratio}`);
    if (
      focus &&
      (!result.focusVisible ||
        result.outline === "none" ||
        parseFloat(result.width) < 2)
    )
      throw Error("Keyboard focus not visibly outlined");
  }
  await page.goto(`http://127.0.0.1:5198/?engagement=${e.id}&view=controls`);
  await page.locator(".workspace-footer").waitFor();
  const opener = page
    .getByRole("button", { name: "CC-1", exact: true })
    .first();
  await tabTo(opener);
  await contrast(opener, "Focused record link", true);
  await page.keyboard.press("Shift+Tab");
  if (await opener.evaluate((el) => el === document.activeElement))
    throw Error("Reverse Tab did not move");
  await page.keyboard.press("Tab");
  if (!(await opener.evaluate((el) => el === document.activeElement)))
    throw Error("Reverse/forward traversal mismatch");
  await page.keyboard.press("Enter");
  let dialog = page.getByRole("dialog");
  await dialog.waitFor();
  if (!(await dialog.getAttribute("aria-labelledby")))
    throw Error("Modal has no heading association");
  // DOM edge probes exercise the compiled Modal handler; these are synthetic stops,
  // not additional application functionality or product accessibility coverage.
  await dialog.evaluate((el) => {
    const probe = document.createElement("div");
    probe.id = "keyboard-probes";
    probe.innerHTML =
      "<button disabled>Disabled probe</button><button hidden>Hidden probe</button><details><summary>Closed detail probe</summary><button>Closed child probe</button></details>";
    el.append(probe);
  });
  for (const key of ["Tab", "Shift+Tab"]) {
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press(key);
      if (!(await dialog.evaluate((el) => el.contains(document.activeElement))))
        throw Error("Focus escaped modal on " + key);
    }
  }
  await dialog.evaluate((el) => {
    const nodes = Array.from(
      el.querySelectorAll(
        "button,input,select,textarea,summary,a[href],[tabindex]",
      ),
    );
    for (const node of nodes) {
      node.dataset.oldTabindex = node.getAttribute("tabindex") ?? "ABSENT";
      node.tabIndex = -1;
    }
    el.focus();
  });
  await page.keyboard.press("Tab");
  if (!(await dialog.evaluate((el) => el === document.activeElement)))
    throw Error("Empty modal focus fallback failed");
  await dialog.evaluate((el) => {
    for (const node of el.querySelectorAll("[data-old-tabindex]")) {
      if (node.dataset.oldTabindex === "ABSENT")
        node.removeAttribute("tabindex");
      else node.setAttribute("tabindex", node.dataset.oldTabindex);
      delete node.dataset.oldTabindex;
    }
    el.querySelector("#keyboard-probes").remove();
  });
  await page.keyboard.press("Escape");
  await dialog.waitFor({ state: "detached" });
  if (!(await opener.evaluate((el) => el === document.activeElement)))
    throw Error("Dialog did not return focus to opener");
  await contrast(page.locator(".page-heading h1"), "Heading");
  await contrast(page.locator(".badge").first(), "Status text");
  await enter(page.getByRole("button", { name: /Notes/ }).first());
  const add = page.getByRole("button", {
    name: "Add observation",
    exact: true,
  });
  await enter(add);
  dialog = page.getByRole("dialog");
  await dialog.waitFor();
  const required = dialog.locator("input[required],textarea[required]").first();
  await required.waitFor();
  const submit = dialog.locator("button[type=submit]");
  await contrast(submit, "Primary button text");
  await contrast(dialog.getByRole("status"), "Draft status text");
  await enter(submit);
  if (commands !== 0 || (await required.evaluate((el) => el.validity.valid)))
    throw Error("Empty required field submitted");
  await tabTo(dialog.getByLabel("Control", { exact: true }));
  await page.keyboard.press("ArrowDown");
  await tabTo(dialog.getByLabel("Subject", { exact: true }));
  await page.keyboard.type("Keyboard-only observation");
  await tabTo(dialog.getByLabel("Observation", { exact: true }));
  await page.keyboard.type("Retain this text after a stale revision response.");
  await enter(submit);

  await dialog
    .getByRole("alert")
    .filter({ hasText: "This engagement changed in another session." })
    .waitFor();
  if (
    (await dialog.getByLabel("Observation", { exact: true }).inputValue()) !==
    "Retain this text after a stale revision response."
  )
    throw Error("Form error erased draft");
  await contrast(dialog.locator(".error").first(), "Error text");
  await page.keyboard.press("Escape");
  await dialog.waitFor({ state: "detached" });
  await enter(page.getByRole("button", { name: /Workpapers/ }).first());
  const region = page.getByRole("region", {
    name: "Protected instructor source archive",
  });
  await region.waitFor();
  await enter(region.getByRole("button", { name: keyEntry.id, exact: true }));
  const graph = page.getByRole("region", {
    name: "Authored relationship explorer",
  });
  await graph.waitFor();
  await enter(graph.getByRole("button", { name: "actor:0", exact: true }));
  const selected = graph.getByRole("article", {
    name: "Selected authored node",
  });
  await enter(selected.getByRole("button", { name: "fact:F1", exact: true }));
  await selected
    .getByRole("heading", { name: "fact:F1", exact: true })
    .waitFor();
  await enter(
    selected.getByRole("button", { name: "Back through relationships" }),
  );
  await selected
    .getByRole("heading", { name: "actor:0", exact: true })
    .waitFor();
  await enter(graph.getByText("Event timing by trigger", { exact: true }));
  await graph
    .getByText("REQUEST · 0 business days from this trigger", { exact: true })
    .waitFor();
  if (errors.length) throw Error(errors.join("\n"));
  const index = await readFile("dist/index.html");
  const assets = {};
  for (const match of index
    .toString()
    .matchAll(/(?:src|href)="(\/assets\/[^"?#]+)"/g)) {
    const name = match[1];
    assets[name] = createHash("sha256")
      .update(await readFile(resolve("dist", "." + name)))
      .digest("hex");
  }
  await writeFile(
    resolve(output, "PASS.json"),
    JSON.stringify(
      {
        qualification:
          "COMPILED_APP_SYNTHETIC_API_FIXTURE_NOT_LIVE_SERVICE_OR_HUMAN_ACCEPTANCE",
        compiled_index_sha256: createHash("sha256").update(index).digest("hex"),
        compiled_assets_sha256: assets,
        checks: [
          "Tab/Shift+Tab",
          "modal containment and focus return",
          "required field and stale-response text preservation",
          "keyboard relationship and text timeline",
        ],
        contrast: measurements,
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ status: "PASS", measurements }, null, 2));
} finally {
  await browser?.close();
  server.kill();
}
