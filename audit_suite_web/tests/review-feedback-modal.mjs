import { mkdtemp, writeFile, readFile, mkdir, chmod } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";

const web = resolve(import.meta.dirname, "..");
const repo = resolve(web, "..");
const output = process.env.SH_REVIEW_MOBILE_OUTPUT
  ? resolve(process.env.SH_REVIEW_MOBILE_OUTPUT)
  : await mkdtemp(join(tmpdir(), "saved-review-modal-"));
await mkdir(output, { recursive: true, mode: 0o700 });
const input = join(output, "ordinary-review-fixture");
const child = spawnSync(
  process.env.SH_REVIEW_PYTHON ?? "python3",
  [
    "-B",
    join(repo, "tests/audit_suite/review_feedback_browser_fixture.py"),
    input,
  ],
  {
    cwd: repo,
    env: {
      ...process.env,
      PYTHONDONTWRITEBYTECODE: "1",
      PYTHONPATH: [repo, join(repo, "src")].join(":"),
    },
    encoding: "utf8",
  },
);
assert.equal(
  child.status,
  0,
  `Own neutral persisted fixture refused: ${child.stderr}`,
);
const records = JSON.parse(
  await readFile(join(input, "PERSISTED_INPUT.json"), "utf8"),
);
const code = `import React,{useState} from 'react';import{createRoot}from'react-dom/client';
import {ReviewFeedback} from '${join(web, "src/ReviewFeedback.tsx")}';
import {Detail} from '${join(web, "src/components.tsx")}';
import '${join(web, "src/style.css")}';
const records=${JSON.stringify(records)};
function SavedReview(){const [selection,setSelection]=useState([0,0,false]);window.chooseSaved=(kind,stage,preparer=false)=>{window.emitted=null;setSelection([kind,stage,preparer]);};
const [i,j,p]=selection,r=records[i],e=r.stages[j][p?'preparer':'reviewer'],review=e.reviews[0];
return <Detail row={review} title={review.id} onClose={()=>{}}><div className="actions"><ReviewFeedback engagement={e} review={review} supported={true} busy={false} viewerId={p?r.preparer_id:r.reviewer_id} resolutionSupported={true} onRespond={value=>window.emitted=value} onResolveHuman={value=>window.emitted=value}/></div></Detail>};createRoot(document.getElementById('app')).render(<SavedReview/>);`;
await writeFile(join(output, "RENDER_SOURCE.tsx"), code, {
  flag: "wx",
  mode: 0o600,
});
await build({
  stdin: { contents: code, resolveDir: web, loader: "tsx" },
  resolveExtensions: [".ts", ".tsx", ".js", ".jsx", ".json"],
  bundle: true,
  format: "iife",
  outfile: join(output, "app.js"),
  jsx: "automatic",
});
await writeFile(
  join(output, "index.html"),
  '<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="app.css"></head><body><div id="app"></div><script src="app.js"></script></body></html>',
  { flag: "wx", mode: 0o600 },
);
const baseline = process.env.SH_REVIEW_MOBILE_BASELINE === "1";
const browser = await chromium.launch({
  executablePath: "/usr/bin/chromium",
  headless: true,
  args: ["--no-sandbox"],
});
const cases = [];
try {
  for (const width of [1400, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    await page.goto("file://" + join(output, "index.html"));
    const region = page.getByRole("region", {
      name: "Recorded review feedback",
    });
    const resolveReview = page.getByRole("button", {
      name: "Resolve recorded review",
      exact: true,
    });
    for (let i = 0; i < records.length; i++) {
      await page.evaluate((i) => window.chooseSaved(i, 0), i);
      await region.waitFor();
      await resolveReview.waitFor();
      await resolveReview.focus();
      await page.keyboard.press("Enter");
      assert.equal(
        (await page.evaluate(() => window.emitted)).response_workpaper_version,
        1,
      );
      await page.evaluate((i) => window.chooseSaved(i, 1, true), i);
      await page
        .getByRole("article", { name: "Recorded response 1" })
        .waitFor();
      await resolveReview.waitFor({ state: "detached" });
      assert.equal(
        await resolveReview.count(),
        0,
        "Current contributor must not independently resolve",
      );
      const expected =
        records[i].stages[1].preparer.reviews[0].history[0]
          .response_workpaper_version_digest;
      const digestCode = region.locator("code").filter({ hasText: expected });
      assert.equal(
        await digestCode.textContent(),
        expected,
        "Wrapping must preserve every digest byte",
      );
      assert.match(await region.innerText(), /Review status: open/);
      assert.match(
        await region.innerText(),
        /professional acceptance is not asserted/,
      );
      await page
        .getByRole("button", { name: "Record feedback", exact: true })
        .click();
      assert.equal(
        (await page.evaluate(() => window.emitted)).response_workpaper_version,
        2,
      );
      const dimensions = await page.getByRole("dialog").evaluate((dialog) => ({
        viewport: innerWidth,
        modal_client: dialog.clientWidth,
        modal_scroll: dialog.scrollWidth,
        page_scroll: document.documentElement.scrollWidth,
        modal_right: dialog.getBoundingClientRect().right,
        close_right: dialog
          .querySelector('[aria-label="Close dialog"]')
          .getBoundingClientRect().right,
      }));
      if (baseline && width === 390) {
        // Proportional-font identifier widths vary across real persisted IDs.
      } else {
        assert(
          dimensions.modal_scroll <= dimensions.modal_client + 1,
          JSON.stringify(dimensions),
        );
        assert(
          dimensions.page_scroll <= dimensions.viewport,
          JSON.stringify(dimensions),
        );
        assert(
          dimensions.close_right <= dimensions.modal_right,
          JSON.stringify(dimensions),
        );
      }
      await page.screenshot({
        path: join(output, `response-${i}-${width}.png`),
        fullPage: true,
      });
      cases.push({
        kind: records[i].kind,
        stage: "saved_version_2_response",
        ...dimensions,
        exact_digest_preserved: true,
        contributor_resolution_refused: true,
      });
      await page.evaluate((i) => window.chooseSaved(i, 2), i);
      await page
        .getByRole("article", { name: "Recorded response 2" })
        .waitFor();
      assert.match(await region.innerText(), /Review status: resolved/);
      assert.equal(await resolveReview.count(), 0);
      const closed = await page.getByRole("dialog").evaluate((dialog) => ({
        modal_client: dialog.clientWidth,
        modal_scroll: dialog.scrollWidth,
      }));
      if (!baseline)
        assert(
          closed.modal_scroll <= closed.modal_client + 1,
          JSON.stringify(closed),
        );
    }
    await page.close();
  }
} finally {
  await browser.close();
}
if (baseline)
  assert(
    cases.some((c) => c.viewport === 390 && c.modal_scroll > c.modal_client),
    "Own real review identifier must reproduce the title overflow",
  );
await writeFile(
  join(output, "PROOF.json"),
  JSON.stringify(
    {
      schema: "SH_SAVED_REVIEW_MODAL_BROWSER_V1",
      status: baseline ? "PRESERVED_PRE_FIX_OVERFLOW" : "PASS",
      hierarchy: "Real Detail > Modal > .actions > ReviewFeedback",
      cases,
      limitation:
        "Own ordinary Engine-persisted neutral reviews rendered by real components; no actual service, company-native or professional acceptance claim",
    },
    null,
    2,
  ) + "\n",
  { flag: "wx", mode: 0o600 },
);
for (const name of ["app.js", "app.css"])
  await chmod(join(output, name), 0o600);
console.log(
  JSON.stringify({
    status: baseline ? "PRESERVED_PRE_FIX_OVERFLOW" : "PASS",
    cases: cases.length,
  }),
);
