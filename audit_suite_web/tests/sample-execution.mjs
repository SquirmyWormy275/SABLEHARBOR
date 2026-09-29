import { mkdtemp, writeFile, rm, chmod } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
const temp = await mkdtemp(join(tmpdir(), "sample-execution-")),
  repo = resolve(import.meta.dirname, "..");
const fixture = {
  id: "E",
  revision: 2,
  permissions: ["learn"],
  tasks: [{ id: "T", title: "Inspect selected original" }],
  artifacts: [{ id: "A", name: "retained.csv" }],
  selections: [
    { id: "S", immutable: { selected_ids: ["one"], targeted_ids: ["two"] } },
  ],
  sample_executions: [],
  sample_execution_inputs: {
    engagement_id: "E",
    engagement_revision: 2,
    status: "AVAILABLE",
    tasks: [
      {
        task_id: "T",
        task_digest: "t-server",
        control_id: "C",
        boundary_id: "B",
      },
    ],
    selections: [
      {
        selection_id: "S",
        selection_digest: "s-server",
        population_id: "P",
        population_digest: "p-server",
        boundary_id: "B",
        sampling_unit: "source record version",
        population_status: "PROVISIONAL",
        selection_provisional: true,
      },
    ],
    workpaper_versions: [
      {
        workpaper_id: "W",
        workpaper_version: 1,
        workpaper_digest: "w-server",
        task_ids: ["T"],
      },
    ],
    artifacts: [{ artifact_id: "A", sha256: "a-server", bytes: 1 }],
    correctable_executions: [],
  },
};
const longLocator =
  "row one; " + "Exact native record and field location. ".repeat(20);
for (let n = 0; n < 560; n++) {
  fixture.artifacts.push({ id: "EX" + n, name: "Named original " + n });
  fixture.sample_execution_inputs.artifacts.push({
    artifact_id: "EX" + n,
    sha256: "hash" + n,
    bytes: 1,
  });
}
for (let n = 0; n < 60; n++) {
  fixture.tasks.push({ id: "TX" + n, title: "Procedure " + n });
  fixture.sample_execution_inputs.tasks.push({
    task_id: "TX" + n,
    task_digest: "pin" + n,
    control_id: "C",
    boundary_id: "B",
  });
}
await build({
  stdin: {
    contents: `import "${join(repo, "src/style.css")}";import React,{useState}from'react';import{createRoot}from'react-dom/client';import{SampleExecutions}from'${join(repo, "src/SampleExecutions.tsx")}';function App(){const[e,setE]=useState(${JSON.stringify(fixture)});window.change=()=>setE(e=>({...e,permissions:['review'],revision:3}));return <main className='workspace'><SampleExecutions engagement={e} supported={true} busy={false} onCommand={async(kind,payload)=>{window.sent={kind,payload};setE(e=>({...e,revision:e.revision+1,sample_executions:[...e.sample_executions,{...payload,id:'X'+e.revision,revision:e.revision-1,independent_review:'NOT_PERFORMED',automatic_testing_credit:false}],sample_execution_inputs:{...e.sample_execution_inputs,engagement_revision:e.revision+1,correctable_executions:kind.endsWith('record')?[{execution_id:'X2',predecessor_digest:'leaf-server'}]:[]}}));return true}}/></main>};createRoot(document.getElementById('app')).render(<App/>);`,
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
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
page.on("pageerror", (e) => console.error("PAGE", e));
try {
  await page.goto("file://" + join(temp, "index.html"));
  await page
    .getByRole("button", { name: "Record sample execution", exact: true })
    .click();

  await page
    .getByLabel("Execution procedure", { exact: true })
    .selectOption("T");
  await page
    .getByLabel("Execution selection", { exact: true })
    .selectOption("S");
  await page.getByLabel("Execution workpaper version").selectOption("W:1");
  await page
    .getByLabel("Execution purpose")
    .fill("Inspect explicit source row");
  await page
    .getByLabel("Procedure actually performed")
    .fill("Read retained CSV row");
  await page.getByLabel("Selected item to add").selectOption("one");
  await page.getByRole("button", { name: "Add selected item" }).click();
  assert.equal(await page.getByLabel("Manual item status").inputValue(), "");
  await page.getByLabel("Manual item status").selectOption("OBSERVED");
  await page.getByLabel("Item observation").fill("Recorded amount was10.");
  await page
    .getByRole("button", { name: "Save sample execution", exact: true })
    .click();
  await page
    .getByRole("alert")
    .filter({ hasText: "need retained support" })
    .waitFor();
  assert.equal(await page.evaluate(() => window.sent), undefined);
  await page.getByRole("button", { name: "Add retained support" }).click();
  assert.ok(
    (await page
      .getByLabel("Retained support", { exact: true })
      .locator("option")
      .count()) <= 51,
  );
  await page
    .getByLabel("Find retained support", { exact: true })
    .fill("Named original 559");
  await page
    .getByLabel("Retained support", { exact: true })
    .getByRole("option", { name: "EX559 · Named original 559", exact: true })
    .waitFor({ state: "attached" });
  await page.getByLabel("Find retained support", { exact: true }).fill("");
  await page.getByLabel("Retained support", { exact: true }).selectOption("A");
  await page.getByLabel("Exact author-supplied locator").fill(longLocator);
  if (process.env.AUDIT_UI_CAPTURE_ROOT) {
    for (const width of [1400, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      const path = join(
        process.env.AUDIT_UI_CAPTURE_ROOT,
        `sample-form-${width}.png`,
      );
      await page.evaluate(async () => {
        await document.fonts.ready;
        await new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve)),
        );
      });
      await page.screenshot({ path, fullPage: true });
      await chmod(path, 0o600);
    }
  }

  await page
    .getByRole("button", { name: "Save sample execution", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  await page
    .getByText("1 retained execution revisions", { exact: true })
    .waitFor();
  const sent = await page.evaluate(() => window.sent);
  assert.equal(sent.payload.workpaper_digest, "w-server");
  assert.equal(sent.payload.items[0].status, "OBSERVED");
  assert.equal(sent.payload.task_digest, "t-server");
  await page.getByText("X2 · revision 1 · T", { exact: true }).click();
  await page
    .getByText(
      "Population UNKNOWN · Independent review NOT_PERFORMED · Automatic testing credit: false",
      { exact: true },
    )
    .waitFor();
  const references = page.locator(".sample-evidence-references");
  const summary = references.locator("summary");
  assert.equal(await summary.innerText(), "Evidence references (1)");
  for (const width of [1400, 390]) {
    await page.setViewportSize({ width, height: 844 });
    assert.equal(
      await page.getByText(longLocator, { exact: true }).isVisible(),
      false,
    );
    assert.equal(
      await page
        .getByText("Recorded amount was10.", { exact: true })
        .isVisible(),
      true,
    );
    const collapsedHeight = await references.evaluate(
      (el) => el.getBoundingClientRect().height,
    );
    await summary.focus();
    await page.keyboard.press("Enter");
    assert.equal(
      await page.getByText(longLocator, { exact: true }).isVisible(),
      true,
    );
    assert.match(await references.innerText(), /A · retained.csv/);
    assert.match(await references.innerText(), /SHA256: a-server/);
    assert.ok(
      (await references.evaluate((el) => el.getBoundingClientRect().height)) >
        collapsedHeight,
    );
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      true,
    );
    await summary.focus();
    await page.keyboard.press("Space");
    assert.equal(await references.getAttribute("open"), null);
    assert.deepEqual(await page.evaluate(() => window.sent), sent);
    if (process.env.AUDIT_UI_CAPTURE_ROOT) {
      const path = join(
        process.env.AUDIT_UI_CAPTURE_ROOT,
        `sample-history-${width}.png`,
      );
      await page.screenshot({ path, fullPage: true });
      await chmod(path, 0o600);
    }
  }
  await page.getByRole("button", { name: "Correct this execution" }).click();
  assert.equal(
    await page.getByLabel("Execution selection", { exact: true }).isDisabled(),
    true,
  );
  assert.equal(
    await page
      .getByRole("button", { name: "Remove item", exact: true })
      .count(),
    0,
  );
  await page
    .getByLabel("Item observation")
    .fill("Corrected explicit observation.");
  await page
    .getByLabel("Correction rationale")
    .fill("Original wording was incomplete.");
  await page.getByRole("button", { name: "Save correction" }).click();
  await page
    .getByText("2 retained execution revisions", { exact: true })
    .waitFor();
  assert.equal(
    (await page.evaluate(() => window.sent)).payload.predecessor_digest,
    "leaf-server",
  );
  await page
    .getByRole("button", { name: "Record sample execution", exact: true })
    .click();
  await page.getByLabel("Execution purpose").fill("Unsaved text");
  await page.evaluate(() => window.change());
  await page
    .getByText(
      "Recording requires an active engagement, current input pins and learner or instructor permission.",
      { exact: true },
    )
    .waitFor();
  assert.equal(await page.getByLabel("Execution purpose").count(), 0);
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  console.log(
    "PASS actual form keyboard record, manual support validation, authoritative pins, expandable exact evidence references, leaf correction/history, permission reset and narrow layout",
  );
} finally {
  await browser.close();
  await rm(temp, { recursive: true, force: true });
}
