// Synthetic authorized projections only. Run after npm run build; no live API calls.
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
const output = resolve(
  "../enterprise/generated/audit-suite/build/instructor-originals",
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
    "5200",
    "--strictPort",
  ],
  { stdio: "ignore" },
);
let browser;

try {
  for (let i = 0; i < 50; i++) {
    try {
      if ((await fetch("http://127.0.0.1:5200")).ok) break;
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

  e.capabilities = { instructor_reference_library: true };
  const originals = new Map();
  keyIndex.entries = Array.from({ length: 1110 }, (_, i) => {
    const id = `MM-13.03.V${String(i + 1).padStart(4, "0")}`;
    const text = `{\n   "title" : "Neutral 雪 é ${i}",\n   "padding": "${"long-byte-line-".repeat(35)}"\n}\n\n`;
    const raw = Buffer.from(text, "utf8");
    originals.set(id, raw);
    return {
      ...keyEntry,
      id,
      raw_sha256: createHash("sha256").update(raw).digest("hex"),
    };
  });
  keyIndex.required = 1110;
  keyIndex.migrated = 1110;
  let reads = 0,
    mode = "normal",
    hold = false,
    held = false,
    release;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/original")) {
      reads++;
      const id = path.split("/").at(-2),
        entry = keyIndex.entries.find((x) => x.id === id),
        raw = originals.get(id);
      const value = {
        ...keyContext,
        scenario_id: id,
        key_sha256: entry.key_sha256,
        raw_sha256: entry.raw_sha256,
        canonical_sha256: entry.canonical_sha256,
        encoding: "base64",
        media_type: "application/json",
        byte_count: raw.length,
        content_base64: raw.toString("base64"),
      };
      if (mode === "bad")
        value.content_base64 = Buffer.from(
          raw.toString().replace("Neutral", "Changed"),
        ).toString("base64");
      if (hold) {
        held = true;
        await new Promise((r) => (release = r));
      }
      return route.fulfill({ json: value }).catch(() => {});
    }
    if (path.endsWith("/instructor-key"))
      return route.fulfill({ json: keyIndex });
    if (path.includes("/instructor-key/")) {
      const id = path.split("/").at(-1),
        entry = keyIndex.entries.find((x) => x.id === id);
      const detail = structuredClone(keyDetail);
      detail.key.id = id;
      detail.key.source.raw_sha256 = entry.raw_sha256;
      return route.fulfill({ json: detail });
    }
    if (route.request().method() !== "GET") throw Error("Unexpected mutation");
    return route.fulfill({
      json:
        path === "/api/bootstrap"
          ? {
              viewer: {
                id: "fixture",
                display_name: "Synthetic instructor",
                roles: ["instructor"],
              },
              csrf_token: "fixture",
              engagements: [e],
              capabilities: e.capabilities,
              programs: [],
              people: [],
              controls: [],
            }
          : e,
    });
  });
  async function tabTo(locator) {
    for (let i = 0; i < 200; i++) {
      if (await locator.evaluate((el) => el === document.activeElement)) return;
      await page.keyboard.press("Tab");
    }
    throw Error("Keyboard target unavailable");
  }
  async function keyClick(locator) {
    await tabTo(locator);
    await page.keyboard.press("Enter");
  }
  await page.goto(`http://127.0.0.1:5200/?engagement=${e.id}&view=review`);
  const archive = page.getByRole("region", {
    name: "Protected instructor source archive",
  });
  await archive
    .getByRole("button", { name: keyIndex.entries[0].id, exact: true })
    .click();
  const disclosure = page.getByText(
    "Inspect original source versions side by side",
    { exact: true },
  );
  await keyClick(disclosure);
  let inspector = page.getByRole("region", {
    name: "Inspect archived source versions",
  });
  await inspector.waitFor();
  if (reads) throw Error("Eager original fetch");
  const leftSearch = inspector.getByLabel("Left archived source search", {
    exact: true,
  });
  const leftSelect = inspector.getByRole("combobox", {
    name: "Left archived source",
    exact: true,
  });
  const rightSearch = inspector.getByLabel("Right archived source search", {
    exact: true,
  });
  const rightSelect = inspector.getByRole("combobox", {
    name: "Right archived source",
    exact: true,
  });
  if ((await leftSelect.locator("option").count()) !== 51)
    throw Error(
      "1110-entry selector not bounded: " +
        (await leftSelect.locator("option").count()) +
        " " +
        (await leftSelect.inputValue()),
    );
  await keyClick(
    inspector.getByRole("button", {
      name: "Load left archived original",
      exact: true,
    }),
  );
  const left = inspector.getByLabel("Left archived original content", {
    exact: true,
  });
  await left.waitFor();
  if (
    (await left.textContent()) !==
    originals.get(keyIndex.entries[0].id).toString()
  )
    throw Error("Noncanonical Unicode original changed");
  await rightSearch.fill("V1110");
  await rightSelect.selectOption(keyIndex.entries[1109].id);
  await keyClick(
    inspector.getByRole("button", {
      name: "Load right archived original",
      exact: true,
    }),
  );
  const right = inspector.getByLabel("Right archived original content", {
    exact: true,
  });
  await right.waitFor();
  if (
    (await right.textContent()) !==
    originals.get(keyIndex.entries[1109].id).toString()
  )
    throw Error("Right source bytes substituted");
  await rightSearch.fill("no-match");
  if (
    (await rightSelect.inputValue()) !== keyIndex.entries[1109].id ||
    (await rightSelect.locator("option").count()) !== 2
  )
    throw Error("Search lost selected source");
  if (reads !== 2) throw Error("Filtering fetched originals");
  await page.setViewportSize({ width: 390, height: 844 });
  if (
    await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)
  )
    throw Error("Narrow original document overflow");
  await tabTo(left);
  if (!(await left.evaluate((el) => el === document.activeElement)))
    throw Error("Original text not keyboard reachable");
  await page.screenshot({
    path: resolve(output, "narrow.png"),
    fullPage: true,
  });
  mode = "bad";
  await inspector
    .getByRole("button", { name: "Load left archived original", exact: true })
    .click();
  await inspector
    .getByText("Original failed its exact byte check.", { exact: true })
    .waitFor();
  if (await left.count()) throw Error("Bad hash retained prior content");
  mode = "normal";
  hold = true;
  held = false;
  await inspector
    .getByRole("button", { name: "Load left archived original", exact: true })
    .click();
  for (let i = 0; i < 50 && !held; i++) await page.waitForTimeout(10);
  if (!held) throw Error("Request not held");
  await leftSearch.fill("V0002");
  await leftSelect.selectOption(keyIndex.entries[1].id);
  release();
  hold = false;
  await page.waitForTimeout(100);
  if (await left.count()) throw Error("Old selection response displayed");
  await inspector
    .getByRole("button", { name: "Load left archived original", exact: true })
    .click();
  await left.waitFor();
  await keyClick(
    page.getByRole("button", {
      name: "Close original source inspection",
      exact: true,
    }),
  );
  if (
    await page
      .getByLabel("Left archived original content", { exact: true })
      .count()
  )
    throw Error("Closing inspector retained original in DOM");
  await keyClick(disclosure);
  inspector = page.getByRole("region", {
    name: "Inspect archived source versions",
  });
  if (await inspector.locator("pre").count())
    throw Error("Reopening restored hidden original");
  await inspector
    .getByRole("button", { name: "Load left archived original", exact: true })
    .click();
  await inspector.locator("pre").waitFor();
  // Context refresh alone must clear originals even while instructor permission remains.
  e.revision++;
  await page.evaluate(() =>
    window.dispatchEvent(new PopStateEvent("popstate")),
  );
  await page.waitForFunction(
    () =>
      !document.querySelector('[aria-label="Left archived original content"]'),
  );
  await archive
    .getByRole("button", { name: keyIndex.entries[0].id, exact: true })
    .click();
  await keyClick(disclosure);
  inspector = page.getByRole("region", {
    name: "Inspect archived source versions",
  });
  hold = true;
  held = false;
  await inspector
    .getByRole("button", { name: "Load left archived original", exact: true })
    .click();
  for (let i = 0; i < 50 && !held; i++) await page.waitForTimeout(10);
  if (!held) throw Error("Close-boundary request not held");
  await page
    .getByRole("button", {
      name: "Close original source inspection",
      exact: true,
    })
    .click();
  release();
  hold = false;
  await page.waitForTimeout(100);
  if (
    await page
      .getByLabel("Left archived original content", { exact: true })
      .count()
  )
    throw Error("Late response repopulated closed inspection");
  await keyClick(disclosure);
  inspector = page.getByRole("region", {
    name: "Inspect archived source versions",
  });
  await inspector
    .getByRole("button", { name: "Load left archived original", exact: true })
    .click();
  await inspector.locator("pre").waitFor();
  e.permissions = ["learn"];
  e.revision++;
  await page.evaluate(() =>
    window.dispatchEvent(new PopStateEvent("popstate")),
  );
  await page.waitForFunction(
    () =>
      !document.querySelector(
        '[aria-label="Protected instructor source archive"]',
      ),
  );
  if (
    await page
      .getByLabel("Left archived original content", { exact: true })
      .count()
  )
    throw Error("Role change retained original");
  if (errors.length) throw Error(errors.join("\n"));
  const index = await readFile("dist/index.html");
  const assets = {};
  for (const match of index
    .toString()
    .matchAll(/(?:src|href)="(\/assets\/[^"?#]+)"/g)) {
    assets[match[1]] = createHash("sha256")
      .update(await readFile(resolve("dist", "." + match[1])))
      .digest("hex");
  }
  await writeFile(
    resolve(output, "PASS.json"),
    JSON.stringify(
      {
        qualification:
          "COMPILED_APP_SYNTHETIC_PROJECTIONS_NOT_LIVE_PROTECTED_ARCHIVE_ACCEPTANCE",
        compiled_index_sha256: createHash("sha256").update(index).digest("hex"),
        compiled_assets_sha256: assets,
        entries: 1110,
        reads,
        checks: [
          "explicit two-source reads",
          "exact Unicode whitespace",
          "bounded search retains selection",
          "bad hash clears",
          "late selection ignored",
          "close clears and cancels delayed responses",
          "context refresh clears",
          "role change clears",
          "keyboard and390px",
        ],
      },
      null,
      2,
    ),
  );
  console.log("Instructor original compiled-App checks PASS");
} finally {
  await browser?.close();
  server.kill();
}
