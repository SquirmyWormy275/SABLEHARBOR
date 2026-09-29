import { mkdtemp, writeFile, rm, chmod } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
const temp = await mkdtemp(join(tmpdir(), "sample-original-context-")),
  repo = resolve(import.meta.dirname, "..");
const trace = {
  revision: 1,
  task_id: "T",
  task_digest: "a".repeat(64),
  workpaper_id: "W",
  workpaper_version: 1,
  workpaper_digest: "b".repeat(64),
  selection_id: "S",
  population_id: "P",
  population_status: "PROVISIONAL",
  actor: "Author",
  recorded_at: "2027-01-02",
  purpose: "Inspect the explicitly selected row",
  procedure: "Read the retained source and record the observed quantity",
  items: [
    {
      item_id: "one",
      status: "OBSERVED",
      observation: "Earlier observation from the retained original.",
      selection_basis: "TARGETED",
      evidence: [{ artifact_id: "A", sha256: "c".repeat(64), locator: "row1" }],
    },
  ],
};
const e = {
  id: "E",
  revision: 3,
  permissions: ["learn"],
  scope: { boundaries: ["corporate"] },
  artifacts: [
    {
      id: "A",
      status: "AVAILABLE",
      sha256: "c".repeat(64),
      name: "retained.csv",
    },
  ],
  requests: [],
  controls: [],
  tasks: [{ id: "T", title: "Inspect selected row" }],
  workpapers: [
    {
      id: "W",
      title: "Retained reconciliation",
      versions: [{ version: 1, evidence_ids: ["A"] }, { version: 2 }],
    },
  ],
  sample_executions: Array.from({ length: 12 }, (_, n) => ({
    ...trace,
    id: "X" + n,
    ...(n === 1
      ? {
          revision: 2,
          predecessor_id: "X0",
          correction_rationale: "Correct the stated quantity",
          items: [
            {
              ...trace.items[0],
              status: "EXCEPTION_RECORDED",
              observation: "Corrected explicit observation from row1.",
            },
          ],
        }
      : {}),
  })),
  sample_execution_inputs: {
    engagement_id: "E",
    engagement_revision: 3,
    tasks: [{ task_id: "T", task_digest: "a".repeat(64) }],
    workpaper_versions: [
      {
        workpaper_id: "W",
        workpaper_version: 1,
        workpaper_digest: "b".repeat(64),
      },
    ],
  },
};
await build({
  stdin: {
    contents: `import React,{useState}from'react';import{createRoot}from'react-dom/client';import '${join(repo, "src/style.css")}';import{EvidenceContext}from'${join(repo, "src/EvidenceContext.tsx")}';function App(){const[e,setE]=useState(${JSON.stringify(e)}),[actor,setActor]=useState('L');window.unpin=()=>setE(e=>({...e,sample_execution_inputs:{...e.sample_execution_inputs,tasks:[],workpaper_versions:[]}}));window.actor=()=>setActor('OTHER');window.revoke=()=>setE(e=>({...e,permissions:[]}));return <main className='workspace'><EvidenceContext engagement={e} artifactId='A' viewerId={actor} onOpen={ref=>window.opened=ref}/></main>};createRoot(document.getElementById('app')).render(<App/>);`,
    resolveDir: repo,
    loader: "tsx",
  },
  resolveExtensions: [".ts", ".tsx", ".js"],
  bundle: true,
  format: "iife",
  outfile: join(temp, "app.js"),
  jsx: "automatic",
});
await writeFile(
  join(temp, "index.html"),
  '<html><head><link rel="stylesheet" href="app.css"></head><body><div id="app"></div><script src="app.js"></script></body></html>',
);
const browser = await chromium.launch({
  executablePath: "/usr/bin/chromium",
  headless: true,
  args: ["--no-sandbox"],
});
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
try {
  await page.goto("file://" + join(temp, "index.html"));
  const panel = page.getByRole("region", {
    name: "Recorded sample item observations",
  });
  await panel.waitFor();
  assert.equal(await panel.locator("article").count(), 10);
  await panel.getByRole("button", { name: "Next observations" }).focus();
  await page.keyboard.press("Enter");
  assert.equal(await panel.locator("article").count(), 2);
  await panel
    .getByLabel("Find observations for this original")
    .fill("Corrected explicit");
  assert.equal(await panel.locator("article").count(), 1);
  await panel
    .getByRole("button", {
      name: "Open workpaper: Retained reconciliation · version 1",
      exact: true,
    })
    .click();
  assert.deepEqual(await page.evaluate(() => window.opened), {
    collection: "workpapers",
    id: "W",
    version: 1,
  });
  await panel
    .getByRole("button", {
      name: "Open procedure: Inspect selected row",
      exact: true,
    })
    .focus();
  await page.keyboard.press("Enter");
  assert.deepEqual(await page.evaluate(() => window.opened), {
    collection: "tasks",
    id: "T",
  });
  if (process.env.AUDIT_UI_CAPTURE_ROOT) {
    for (const width of [1400, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await panel.scrollIntoViewIfNeeded();
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve)),
          ),
      );
      const path = join(
        process.env.AUDIT_UI_CAPTURE_ROOT,
        "sample-original-" + width + ".png",
      );
      await panel.screenshot({ path });
      await chmod(path, 0o600);
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        ),
        false,
      );
    }
  }
  await page.evaluate(() => window.unpin());
  await panel
    .getByText(
      "Procedure T: exact recorded pin is unavailable in the current input index.",
      { exact: true },
    )
    .waitFor();
  assert.equal(
    await panel
      .getByRole("button", { name: /Open (procedure|workpaper):/ })
      .count(),
    0,
  );
  assert.equal(
    await panel
      .getByText("Corrected explicit observation from row1.", { exact: true })
      .count(),
    1,
  );
  await panel
    .getByText("Recorded procedure, correction and source pins", {
      exact: true,
    })
    .click();
  await panel
    .getByText("Correction rationale: Correct the stated quantity", {
      exact: true,
    })
    .waitFor();
  await page.evaluate(() => window.actor());
  await page.waitForFunction(
    () =>
      document.querySelector(".sample-evidence-context input")?.value === "",
  );
  assert.equal(await panel.locator("article").count(), 10);
  await page.evaluate(() => window.revoke());
  await panel.getByRole("status").waitFor();
  assert.equal(await panel.locator("article").count(), 0);
  console.log(
    "PASS exact-original context pagination/search, keyboard pinned old-version navigation, stale pin no substitution, correction history, actor reset, revocation and styled narrow layout",
  );
} finally {
  await browser.close();
  await rm(temp, { recursive: true, force: true });
}
