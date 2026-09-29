import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
const temp = await mkdtemp(join(tmpdir(), "bound-key-"));
const repo = resolve(import.meta.dirname, "..");
const sources = Array.from({ length: 56 }, (_, i) => ({
  id: `S${i}`,
  company: "C",
  branch: "B",
  system: "SYS",
  record: `R${i}`,
  version: 1,
  sha256: "b".repeat(64),
  event_at: "2027-01-01T00:00:00Z",
  available_at: "2027-01-02T00:00:00Z",
  imported_at: "2027-02-01T00:00:00Z",
  actor_granted_at_binding: true,
  actor_visibility_at_binding: "DISCOVERABLE_LATEST",
  retained_audit_artifact_ids: [],
  fact_verification: "Exact reference only",
}));
const bound = {
  binding: {
    manifest_sha256: "a".repeat(64),
    engagement_id: "ENG1",
    bound_revision: 2,
    current_revision: 2,
    status: "MATCHING_REVISION",
  },
  snapshot: {
    status: "BOUND_INSTRUCTOR_AUTHORED_UNVALIDATED",
    professional_validation: "UNVALIDATED",
    authored_status: "INSTRUCTOR_AUTHORED_INFERENCE",
    grading: "NOT_PERFORMED",
    engagement: {
      id: "ENG1",
      revision: 2,
      scope: {
        boundaries: ["corporate"],
        period_start: "2027-01-01",
        period_end: "2027-12-31",
      },
      simulated_at: "2028-01-01",
    },
    sources,
    authored: {
      issues: Array.from({ length: 4 }, (_, i) => ({
        id: `ISSUE${i}`,
        control_ids: [`C${i}`],
        source_ids: sources.filter((_, n) => n % 4 === i).map((r) => r.id),
        claim: `Explicit interpretation ${i}`,
        uncertainty: "No whole-control conclusion",
      })),
      expectations: Array.from({ length: 4 }, (_, i) => ({
        id: `EXPECT${i}`,
        issue_ids: [`ISSUE${i}`],
        procedure: `Exact procedure ${i}`,
        acceptable_alternatives: ["A supported alternative"],
      })),
      uncertainty: ["Unvalidated"],
      source_pins: {},
    },
    software_verified: ["Native pins"],
    limits: ["No grading"],
  },
};
const engagement = {
  id: "ENG1",
  revision: 2,
  permissions: ["instruct"],
  scope: bound.snapshot.engagement.scope,
  artifacts: [],
  controls: Array.from({ length: 4 }, (_, i) => ({
    id: `C${i}`,
    title: `Actual control ${i}`,
  })),
  tasks: [],
};
const code = `import React from 'react';import {createRoot} from 'react-dom/client';import Key from '${join(repo, "src/BoundInstructorKey.tsx")}';const bound=${JSON.stringify(bound)}, engagement=${JSON.stringify(engagement)};window.calls=0;window.fetch=async()=>{window.calls++;if(window.hold)await new Promise(r=>window.release=r);return {ok:true,json:async()=>bound};};const root=createRoot(document.getElementById('app'));window.draw=(allowed=true,revision=2)=>root.render(<Key engagement={{...engagement,revision,permissions:allowed?['instruct']:['learn']}} viewerId={allowed?'INSTRUCTOR':'LEARNER'}/>);window.draw();`;
await build({
  resolveExtensions: [".ts", ".tsx", ".js", ".jsx", ".json"],
  stdin: { contents: code, resolveDir: repo, loader: "tsx" },
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
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
try {
  await page.goto("file://" + join(temp, "index.html"));
  const index = page.getByRole("region", { name: "Authored issue index" }),
    list = page.getByRole("list", { name: "Matching bound originals" });
  await index.waitFor();
  assert.equal(await list.getByRole("button").count(), 10);
  await page.getByRole("button", { name: "Next sources", exact: true }).focus();
  await page.keyboard.press("Enter");
  await page.getByText("Page 2 of 6", { exact: true }).waitFor();
  await page.getByLabel("Find bound source", { exact: true }).fill("R55");
  await page.getByText("Page 1 of 1", { exact: true }).waitFor();
  assert.equal(await list.getByRole("button").count(), 1);
  await index.getByRole("button").nth(1).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { name: "ISSUE1", exact: true }).waitFor();
  assert.equal(
    await page.getByLabel("Find bound source", { exact: true }).inputValue(),
    "",
  );
  await page.getByText("Page 1 of 2", { exact: true }).waitFor();
  assert.equal(await list.getByRole("button").count(), 10);
  assert.equal(
    await page.getByRole("heading", { name: "ISSUE0", exact: true }).count(),
    0,
  );
  await page.getByText("EXPECT1", { exact: true }).click();
  await page.getByText("Exact procedure 1", { exact: true }).waitFor();
  await list.getByRole("button").first().click();
  await page.getByRole("article", { name: "Selected bound source" }).waitFor();
  await page
    .getByLabel("Find bound source", { exact: true })
    .fill("no-such-source");
  await page
    .getByText("The selected original is outside the current filter.", {
      exact: false,
    })
    .waitFor();
  assert.equal(await list.getByRole("button").count(), 0);
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
    false,
  );
  const calls = await page.evaluate(() => window.calls);
  await page.evaluate(() => window.draw(false));
  await page
    .getByText("Instructor access is required.", { exact: true })
    .waitFor();
  assert.equal(
    await page.getByText("Explicit interpretation 1", { exact: true }).count(),
    0,
  );
  assert.equal(await page.evaluate(() => window.calls), calls);
  await page.evaluate(() => {
    window.hold = true;
    window.draw(true, 3);
  });
  await page
    .getByText("Loading protected engagement binding…", { exact: true })
    .waitFor();
  await page.waitForFunction(() => !!window.release);
  await page.evaluate(() => window.draw(false, 3));
  await page.evaluate(() => window.release());
  await page
    .getByText("Instructor access is required.", { exact: true })
    .waitFor();
  assert.equal(
    await page.getByRole("region", { name: "Authored issue index" }).count(),
    0,
  );
  console.log(
    "56-source navigation, keyboard, resets, retained selection, narrow layout and stale-role response PASS",
  );
} finally {
  await browser.close();
  await rm(temp, { recursive: true, force: true });
}
