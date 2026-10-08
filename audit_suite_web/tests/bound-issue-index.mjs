// Real React and global CSS; every supplied Key response is declared metadata.
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
const repo = resolve(import.meta.dirname, "..");
const out = process.env.BOUND_ISSUE_INDEX_BROWSER_OUTPUT;
assert.ok(out?.startsWith("/home/kingoftheeast/"));
await mkdir(out, { mode: 0o700 });
const fixture = JSON.parse(
  await readFile(
    join(import.meta.dirname, "fixtures/declared-bound-issue76.json"),
  ),
);
const code = `import React from 'react';import {createRoot} from 'react-dom/client';
import Key from '${repo}/src/BoundInstructorKey.tsx';import '${repo}/src/style.css';
const {bound:value,engagement:e}=${JSON.stringify(fixture)};let revision=2;window.calls=[];window.saved=[];
window.fetch=async(path,options={})=>{window.calls.push({path,options});let result;
if(path.endsWith('/instructor-binding'))result={...value,binding:{...value.binding,current_revision:revision,status:revision===2?'MATCHING_REVISION':'HISTORICAL_REVISION'}};
else if(options.method==='POST'){const body=JSON.parse(options.body);if(path.endsWith('/restore')){const r=window.saved.find(r=>path.includes('/'+r.id+'/'));result={...r,current_engagement_revision:revision,navigation:r.user};}
else {result={id:'OWN-VIEW',engagement_id:e.id,kind:'BOUND',version:1,status:'ACTIVE',saved_engagement_revision:revision,current_engagement_revision:revision,context_status:'CURRENT',revision_status:'MATCHING_REVISION',restorable:true,personal_content_visible:true,navigation:null,user:body.user,key_pin:body.key_pin};window.saved=[result];}}
else result={engagement_id:e.id,current_engagement_revision:revision,kind:'BOUND',views:window.saved};
return {ok:true,json:async()=>structuredClone(result)};};
const root=createRoot(document.getElementById('app'));window.draw=(rev=2,allowed=true,actor='OWN-INSTRUCTOR',ref='')=>{revision=rev;root.render(<Key engagement={{...e,revision:rev,permissions:allowed?['instruct']:['learn']}} viewerId={actor} savedViewsEnabled={true} referenceCurrent={ref}/>)};window.draw();`;
await build({
  plugins: [
    {
      name: "exact-case-relative-files",
      setup(b) {
        b.onResolve({ filter: /^\./ }, (a) => {
          for (const suffix of ["", ".ts", ".tsx", ".js", ".jsx", ".json"]) {
            const path = resolve(a.resolveDir, a.path + suffix);
            if (existsSync(path)) return { path };
          }
        });
      },
    },
  ],
  stdin: { contents: code, resolveDir: repo, loader: "tsx" },
  bundle: true,
  format: "iife",
  jsx: "automatic",
  outfile: join(out, "app.js"),
});
await writeFile(
  join(out, "index.html"),
  '<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="app.css"><body><main id="app"></main><script src="app.js"></script></body></html>',
  { mode: 0o600, flag: "wx" },
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
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    let network = 0;
    await page.route(/^https?:/, (r) => {
      network++;
      return r.abort();
    });
    await page.goto("file://" + join(out, "index.html"));
    const index = page.getByRole("region", { name: "Authored issue index" });
    const list = index.getByRole("list", { name: "Matching authored issues" });
    await index.waitFor();
    assert.equal(await list.getByRole("button").count(), 20);
    const dimensions = await index.evaluate((el) => ({
      index_height: el.getBoundingClientRect().height,
      workspace_top:
        document.querySelector(".bound-key-workspace").getBoundingClientRect()
          .top + scrollY,
      scroll_width: document.documentElement.scrollWidth,
    }));
    assert.ok(dimensions.scroll_width <= width);
    for (let i = 0; i < 3; i++)
      await index
        .getByRole("button", { name: "Next issues", exact: true })
        .click();
    await index.getByText("Issue page 4 of 4", { exact: true }).waitFor();
    assert.equal(await list.getByRole("button").count(), 16);
    const search = index.getByLabel("Find authored issue", { exact: true });
    await search.fill("OWN-CARD-76");
    assert.equal(await list.getByRole("button").count(), 1);
    await search.focus();
    for (let i = 0; i < 3; i++) await page.keyboard.press("Tab");
    assert.ok(
      (await page.evaluate(() => document.activeElement?.textContent)).includes(
        "OWN-CARD-76",
      ),
    );
    await page.keyboard.press("Space");
    await page
      .getByRole("heading", { name: "OWN-CARD-76", exact: true })
      .waitFor();
    await page
      .getByRole("list", { name: "Matching bound originals" })
      .getByRole("button")
      .first()
      .click();
    const original = page.getByRole("article", {
      name: "Selected bound source",
    });
    await original.waitFor();
    const originalText = await original.textContent();
    await search.fill("no-such-issue");
    await index
      .getByText("No authored issues match.", { exact: false })
      .waitFor();
    assert.equal(await list.getByRole("button").count(), 0);
    assert.equal(await original.textContent(), originalText);
    await index
      .getByRole("button", {
        name: "Show selected issue OWN-CARD-76 in index",
        exact: true,
      })
      .focus();
    await page.keyboard.press("Enter");
    await index.getByText("Issue page 4 of 4", { exact: true }).waitFor();
    assert.equal(await search.inputValue(), "");
    assert.equal(await original.textContent(), originalText);
    await index
      .getByLabel("Issue control", { exact: true })
      .selectOption("CONTROL-2");
    assert.equal(await list.getByRole("button").count(), 19);
    await index
      .getByRole("button", { name: "Clear issue filters", exact: true })
      .click();
    for (let i = 0; i < 3; i++)
      await index
        .getByRole("button", { name: "Next issues", exact: true })
        .click();
    await page.getByText("Saved Key views", { exact: true }).click();
    await page
      .getByLabel("Saved Key view name", { exact: true })
      .fill("Owned page four");
    await page
      .getByRole("button", { name: "Save current Key view", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "Owned page four", exact: true })
      .waitFor();
    assert.deepEqual(
      await page.evaluate(() => window.saved[0].user.issue_index),
      { query: "", control_id: null, page: 3 },
    );
    await search.fill("nothing");
    await page
      .getByLabel(
        "Allow explicit restore to replace my current unsaved Key filters and name",
      )
      .check();
    await page
      .getByRole("button", { name: "Restore Key view OWN-VIEW", exact: true })
      .click();
    await index.getByText("Issue page 4 of 4", { exact: true }).waitFor();
    assert.equal(await original.textContent(), originalText);
    await page.evaluate(() => {
      const r = window.saved[0];
      const { issue_index, ...legacy } = r.user;
      window.saved = [{ ...r, user: { ...legacy, title: "Owned old shape" } }];
    });
    await page
      .getByRole("button", { name: "Load saved Key views", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "Owned old shape", exact: true })
      .waitFor();
    await page
      .getByRole("button", { name: "Restore Key view OWN-VIEW", exact: true })
      .click();
    await index.getByText("Issue page 1 of 4", { exact: true }).waitFor();
    await search.fill("hide-all");
    await page.evaluate(() =>
      window.draw(2, true, "OWN-INSTRUCTOR", "OWN-CARD-75"),
    );
    await page
      .getByRole("heading", { name: "OWN-CARD-75", exact: true })
      .waitFor();
    await index.getByText("Issue page 4 of 4", { exact: true }).waitFor();
    assert.equal(await search.inputValue(), "");
    assert.equal(await original.textContent(), originalText);
    await index.evaluate((el) => el.scrollIntoView({ block: "start" }));
    await page.screenshot({
      path: join(out, `SELECTED-${width}.png`),
      fullPage: false,
    });
    await search.fill("OWN-CARD-76");
    await search.focus();
    await index.evaluate((el) => el.scrollIntoView({ block: "start" }));
    await page.screenshot({
      path: join(out, `SEARCH-${width}.png`),
      fullPage: false,
    });
    await page.evaluate(() => window.draw(3, true, "OTHER-INSTRUCTOR"));
    await index.getByText("Issue page 1 of 4", { exact: true }).waitFor();
    assert.equal(await search.inputValue(), "");
    assert.equal(
      await page
        .getByRole("article", { name: "Selected bound source" })
        .count(),
      0,
    );
    const before = await page.evaluate(() => window.calls.length);
    await page.evaluate(() => window.draw(3, false, "OWN-LEARNER"));
    await page
      .getByText("Instructor access is required.", { exact: true })
      .waitFor();
    assert.equal(await index.count(), 0);
    assert.equal(await page.evaluate(() => window.calls.length), before);
    assert.equal(network, 0);
    assert.deepEqual(errors, []);
    observations.push({
      width,
      dimensions,
      declared_issue_count: 76,
      page_size: 20,
      last_page: 16,
      keyboard_tabs_to_searched_target: 3,
      selected_original_preserved: true,
      explicit_saved_restore: true,
      old_missing_index_defaults: true,
      reference_exact_target_page: true,
      actor_revision_reset: true,
      learner_no_private_DOM_or_new_fetch: true,
      network_requests: network,
    });
    await page.close();
  }
  await writeFile(
    join(out, "REPORT.json"),
    JSON.stringify(
      {
        schema: "SH_OWN_BOUND_ISSUE_INDEX_JOURNEY_V1",
        status: "PASS_DECLARED_METADATA_ONLY",
        actual_Key_company_or_SQL_opened: false,
        backend_boundary:
          "Separate genuine native-first private saved-store checks; browser fetch responses are declared metadata.",
        global_css_real_React: true,
        observations,
      },
      null,
      2,
    ) + "\n",
    { mode: 0o600, flag: "wx" },
  );
  console.log(JSON.stringify({ status: "PASS", observations }));
} finally {
  await browser.close();
}
