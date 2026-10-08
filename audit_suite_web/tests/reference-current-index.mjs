// Bounded UI journey with declared metadata; no company, audit or Key originals.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
const repo = resolve(import.meta.dirname, "..");
const require = createRequire(join(repo, "package.json"));
const { build } = require("esbuild");
const { chromium } = require("@playwright/test");
const out = process.env.CURRENT_INDEX_BROWSER_OUTPUT;
assert.ok(out?.startsWith("/home/kingoftheeast/"));
await mkdir(out, { mode: 0o700 });
const source = `import React from 'react';import {createRoot} from 'react-dom/client';
import {ReferenceCrosswalk} from '${repo}/src/ReferenceCrosswalk.tsx';
import '${repo}/src/style.css';
const cards=Array.from({length:76},(_,i)=>({id:'CARD-'+String(i+1).padStart(2,'0'),sha256:'a'.repeat(64),control_ids:[i===75?'SH-IAM-003':'SH-CFG-'+String(i+1).padStart(3,'0')],task_ids:['PROC-'+String(i+1).padStart(3,'0')]}));
const rows=cards.flatMap((c,i)=>[10,22].includes(i)?[]:[{legacy_id:'LEGACY-'+String(i+1).padStart(2,'0'),raw_sha256:'b'.repeat(64),canonical_sha256:'c'.repeat(64),key_sha256:'d'.repeat(64),relations:[{current_id:c.id,status:i%2?'SHARED_CONTROL_ONLY':'OUT_OF_SCOPE',reason:'Declared metadata only',proof:{legacy_pointer:'/scope',current_pointer:'/scope'}}]}]);
const value={schema:'SH_PRIVATE_INSTRUCTOR_REFERENCE_CROSSWALK_V1',projection:'DECLARED_NAVIGATION_ONLY',sha256:'e'.repeat(64),engagement_id:'OWN-UI',archive_sha256:'f'.repeat(64),professional_acceptance:'NOT_ASSERTED',current_cards:cards,rows,inverse:cards.map(c=>({current_id:c.id,legacy_ids:rows.filter(r=>r.relations[0].current_id===c.id).map(r=>r.legacy_id),unmapped_reason:rows.some(r=>r.relations[0].current_id===c.id)?null:'No declared current relation'}))};
const root=createRoot(document.getElementById('app'));window.draw=(mode='CURRENT',selected='',sha='e'.repeat(64))=>root.render(<ReferenceCrosswalk value={{...value,sha256:sha}} mode={mode} selected={selected} onCurrent={id=>{window.selected=id;window.draw('CURRENT',id)}} onLegacy={id=>{window.selected=id;window.draw('ARCHIVE',id)}}/>);window.draw();`;
await build({
  stdin: { contents: source, resolveDir: repo, loader: "tsx" },
  bundle: true,
  format: "iife",
  jsx: "automatic",
  outfile: join(out, "app.js"),
});
await writeFile(
  join(out, "index.html"),
  '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="app.css"></head><body><main id="app"></main><script src="app.js"></script></body></html>',
  { mode: 0o600 },
);
const browser = await chromium.launch({
  executablePath: "/usr/bin/chromium",
  headless: true,
  args: ["--no-sandbox"],
});
const observations = [];
try {
  for (const width of [390, 1440]) {
    const page = await browser.newPage({
      viewport: { width, height: width === 390 ? 844 : 1050 },
    });
    let httpRequests = 0;
    await page.route(/^https?:/, (r) => {
      httpRequests++;
      return r.abort();
    });
    await page.goto("file://" + join(out, "index.html"));
    const panel = page.locator("details.reference-crosswalk");
    await panel.locator(":scope > summary").click();
    assert.equal(await panel.locator(":scope > ul > li").count(), 20);
    await panel.getByText("Page 1 of 4", { exact: true }).waitFor();
    await panel
      .getByRole("button", { name: "Next current cards", exact: true })
      .click();
    await panel.getByText("Page 2 of 4", { exact: true }).waitFor();
    await panel
      .getByRole("button", { name: "Next current cards", exact: true })
      .click();
    await panel
      .getByRole("button", { name: "Next current cards", exact: true })
      .click();
    await panel.getByText("Page 4 of 4", { exact: true }).waitFor();
    assert.equal(await panel.locator(":scope > ul > li").count(), 16);
    assert.equal(
      await panel
        .getByRole("button", { name: "Next current cards", exact: true })
        .isDisabled(),
      true,
    );
    const search = panel.getByLabel("Search current reference cards");
    await search.fill("SH-IAM-003");
    await panel.getByText("1 current card matches.", { exact: true }).waitFor();
    await panel.getByText("Page 1 of 1", { exact: true }).waitFor();
    assert.equal(await panel.locator(":scope > ul > li").count(), 1);
    await search.focus();
    for (let i = 0; i < 3; i++) await page.keyboard.press("Tab");
    assert.equal(
      await page.evaluate(() => document.activeElement?.textContent),
      "CARD-76",
    );
    await page.screenshot({
      path: join(out, `CURRENT-SEARCH-VIEWPORT-${width}.png`),
      fullPage: false,
    });
    await page.keyboard.press("Space");
    await page.waitForFunction(() => window.selected === "CARD-76");
    assert.equal(
      await panel.getByLabel("Search reference links").inputValue(),
      "",
    );
    await panel.locator(":scope > summary").click();
    assert.equal(await panel.locator(":scope > ul > li").count(), 1);
    await page.evaluate(() => window.draw());
    await panel.locator(":scope > summary").click();
    await panel.getByLabel("Relation status").selectOption("UNMAPPED");
    await panel.getByText("2 current cards match.", { exact: true }).waitFor();
    await panel
      .getByLabel("Search current reference cards")
      .fill("DOES-NOT-EXIST");
    await panel
      .getByRole("status")
      .getByText("No current cards match.", { exact: false })
      .waitFor();
    assert.equal(await panel.locator(":scope > ul > li").count(), 0);
    await panel
      .getByRole("button", { name: "Clear reference filters", exact: true })
      .click();
    await panel.getByText("76 current cards match.", { exact: true }).waitFor();
    await panel.getByText("Page 1 of 4", { exact: true }).waitFor();
    assert.equal(await panel.getByLabel("Relation status").inputValue(), "all");
    const dimensions = await page.evaluate(() => ({
      width: innerWidth,
      height: innerHeight,
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight,
    }));
    assert.ok(dimensions.scrollWidth <= width);
    await page.screenshot({
      path: join(out, `CURRENT-PAGED-VIEWPORT-${width}.png`),
      fullPage: false,
    });
    assert.equal(httpRequests, 0);
    observations.push({
      width,
      dimensions,
      visible_index_cards: 20,
      total_cards: 76,
      last_page_cards: 16,
      search_by_control_matches: 1,
      keyboard_tabs_from_search_to_target: 3,
      unmapped_matches: 2,
      empty_and_clear_verified: true,
      selected_card_context_reset: true,
      http_requests: 0,
    });
    await page.close();
  }
  await writeFile(
    join(out, "REPORT.json"),
    JSON.stringify(
      {
        schema: "SH_OWN_CURRENT_REFERENCE_INDEX_NAVIGATION_JOURNEY_V1",
        status: "PASS_DECLARED_METADATA_SEARCH_PAGING_KEYBOARD_AND_CONTEXT",
        declared_metadata_only: true,
        actual_company_or_audit_or_Key_opened: false,
        full_actual_app_or_409_acceptance: false,
        observations,
      },
      null,
      2,
    ) + "\n",
    { mode: 0o600 },
  );
  console.log(
    JSON.stringify({
      status: "PASS",
      viewports: observations.length,
      report: join(out, "REPORT.json"),
    }),
  );
} finally {
  await browser.close();
}
