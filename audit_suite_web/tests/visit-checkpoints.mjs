// Synthetic authorized projections only. Run after npm run build; no live API calls.
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
const output = resolve(
  "../enterprise/generated/audit-suite/build/visit-checkpoints",
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
    "5199",
    "--strictPort",
  ],
  { stdio: "ignore" },
);
let browser;

try {
  for (let i = 0; i < 50; i++) {
    try {
      if ((await fetch("http://127.0.0.1:5199")).ok) break;
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

  e.capabilities = { visit_checkpoints: true };
  e.artifacts[0].status = "AVAILABLE";
  e.artifacts[0].version = 2;
  let version = 0,
    reads = 0,
    compares = 0,
    mode = "current",
    lost = false,
    hold = false,
    held,
    releaseHeld;
  const saves = [],
    unexpected = [];
  const metadata = () => ({
    engagement_id: e.id,
    current_engagement_revision: e.revision,
    version,
    status: version ? "CURRENT" : "NO_CHECKPOINT",
    formal_work_mutated: false,
    supported_kinds: ["artifact", "control"],
    checkpoint_engagement_revision: 3,
    saved_at: "2027-02-11T09:00:00Z",
  });
  const pin = (kind, id, version = null) => ({
    reference: { kind, id, version, sha256: "a".repeat(64) },
    record_sha256: "b".repeat(64),
  });
  const changes = [
    {
      change: "CHANGED",
      prior: pin("artifact", "A-01", 1),
      current: pin("artifact", "A-01", 2),
    },
    ...Array.from({ length: 100 }, (_, i) => ({
      change: "ADDED",
      prior: null,
      current: pin("control", "UNSELECTED-" + i),
    })),
  ];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname,
      method = route.request().method();
    if (path.endsWith("/visit-checkpoint/compare")) {
      compares++;
      const body = route.request().postDataJSON();
      if (
        body.expected_version !== version ||
        body.expected_engagement_revision !== e.revision
      )
        throw Error("Comparison CAS mismatch");
      const value =
        mode === "redacted"
          ? { ...metadata(), status: "CONTEXT_CHANGED" }
          : {
              ...metadata(),
              changes,
              counts: { added: 100, changed: 1, unchanged: 5 },
            };
      if (mode === "bad-pin" && value.changes) {
        value.changes = structuredClone(value.changes);
        value.changes[0].current.reference.sha256 = "c".repeat(64);
      }
      if (hold) {
        held = true;
        await new Promise((r) => (releaseHeld = r));
      }
      return route.fulfill({ json: value });
    }
    if (path.endsWith("/visit-checkpoint")) {
      if (method === "GET") {
        reads++;
        return route.fulfill({ json: metadata() });
      }
      const body = route.request().postDataJSON();
      saves.push(body);
      if (!lost) {
        lost = true;
        version++;
        return route.abort("failed");
      }
      if (JSON.stringify(saves[0]) !== JSON.stringify(body))
        throw Error("Ambiguous retry changed original envelope");
      return route.fulfill({ json: metadata() });
    }
    if (method !== "GET") {
      unexpected.push(path);
      return route.fulfill({
        status: 500,
        json: { error: "No formal operation permitted" },
      });
    }
    if (path === "/api/bootstrap")
      return route.fulfill({
        json: {
          viewer: {
            id: "REVIEWER",
            display_name: "Neutral reviewer",
            roles: ["reviewer"],
          },
          csrf_token: "fixture",
          engagements: [e],
          capabilities: e.capabilities,
          programs: [],
          people: [],
          controls: [],
        },
      });
    return route.fulfill({ json: e });
  });
  await page.goto(`http://127.0.0.1:5199/?engagement=${e.id}&view=controls`);
  await page.locator(".workspace-footer").waitFor();
  await page.getByText("Changes since my checkpoint", { exact: true }).click();
  let panel = page.getByRole("region", { name: "Personal change checkpoint" });
  if (reads || compares || saves.length)
    throw Error("Opening panel silently captured or inspected checkpoint");
  await panel
    .getByRole("button", { name: "Refresh my checkpoint", exact: true })
    .click();
  await panel.getByText("No checkpoint saved yet.", { exact: true }).waitFor();
  await panel
    .getByRole("button", { name: "Save current checkpoint", exact: true })
    .click();
  await panel
    .getByText("The save result is unresolved.", { exact: false })
    .waitFor();
  if (
    !(await panel
      .getByRole("button", { name: "Refresh my checkpoint", exact: true })
      .isDisabled())
  )
    throw Error("Ambiguous save allows unrelated read");
  await panel
    .getByRole("button", { name: "Retry exact checkpoint save", exact: true })
    .click();
  await panel.getByText(/Saved checkpoint 1/).waitFor();
  if (saves.length !== 2 || version !== 1)
    throw Error("Retry duplicated capture");
  await panel
    .getByRole("button", { name: "Compare with current records", exact: true })
    .click();
  await panel
    .getByText("Page 1 of 2 · 101 differences total.", { exact: true })
    .waitFor();
  if ((await panel.locator("li").count()) !== 100)
    throw Error("First page is not bounded");
  await panel
    .getByRole("button", { name: "Next changes", exact: true })
    .click();
  if ((await panel.locator("li").count()) !== 1)
    throw Error("Final page count wrong");
  await panel
    .getByRole("button", { name: "Previous changes", exact: true })
    .click();
  if (
    !(await panel
      .getByRole("button", { name: "Inspect UNSELECTED-0", exact: true })
      .isDisabled())
  )
    throw Error("Unselected record became previewable");
  await panel
    .getByRole("button", { name: "Inspect A-01", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByText("A-01", { exact: true })
    .first()
    .waitFor();
  await page.keyboard.press("Escape");
  mode = "bad-pin";
  await panel
    .getByRole("button", { name: "Compare with current records", exact: true })
    .click();
  await panel
    .getByText("Page 1 of 2 · 101 differences total.", { exact: true })
    .waitFor();
  if (
    !(await panel
      .getByRole("button", { name: "Inspect A-01", exact: true })
      .isDisabled())
  )
    throw Error("Contradictory artifact SHA enabled current preview");
  mode = "redacted";
  await panel
    .getByRole("button", { name: "Compare with current records", exact: true })
    .click();
  await panel
    .getByText("Details and counts are withheld.", { exact: false })
    .waitFor();
  if (
    (await panel.locator("li").count()) ||
    (await panel.getByText("101 differences total.", { exact: false }).count())
  )
    throw Error("Redacted comparison retained inventory");
  // Re-arm a pending response, then switch engagement in the same App instance.
  mode = "current";
  await panel
    .getByRole("button", { name: "Refresh my checkpoint", exact: true })
    .click();
  await panel
    .getByRole("button", { name: "Compare with current records", exact: true })
    .waitFor();
  hold = true;
  await panel
    .getByRole("button", { name: "Compare with current records", exact: true })
    .click();
  for (let i = 0; i < 50 && !held; i++) await page.waitForTimeout(10);
  if (!held) throw Error("Delayed request was not issued");
  e.id = "ENG-OTHER";
  e.revision = 9;
  await page.evaluate((id) => {
    history.pushState({}, "", `?engagement=${id}&view=controls`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, e.id);
  await page.waitForFunction(() => location.search.includes("ENG-OTHER"));
  await page.getByText("Changes since my checkpoint", { exact: true }).click();
  await page
    .getByRole("button", { name: "Refresh my checkpoint", exact: true })
    .waitFor();
  releaseHeld();
  await page.waitForTimeout(100);
  panel = page.getByRole("region", { name: "Personal change checkpoint" });
  if (
    (await panel.locator("li").count()) ||
    (await panel.getByText(/Saved checkpoint/).count())
  )
    throw Error("Old context response entered new workspace");
  if (unexpected.length || errors.length)
    throw Error(JSON.stringify({ unexpected, errors }));
  const index = await readFile("dist/index.html");
  await writeFile(
    resolve(output, "PASS.json"),
    JSON.stringify(
      {
        qualification:
          "COMPILED_APP_SYNTHETIC_ENDPOINTS_NOT_LIVE_API_ACCEPTANCE",
        compiled_index_sha256: createHash("sha256").update(index).digest("hex"),
        saves: saves.length,
        compares,
        formal_commands: unexpected.length,
        checks: [
          "explicit capture",
          "same-envelope ambiguous retry",
          "artifact identity across versions",
          "bounded pagination",
          "exact current preview",
          "redacted counts",
          "late old context isolation",
        ],
      },
      null,
      2,
    ),
  );
  console.log("Visit checkpoint compiled-App journey PASS");
} finally {
  await browser?.close();
  server.kill();
}
