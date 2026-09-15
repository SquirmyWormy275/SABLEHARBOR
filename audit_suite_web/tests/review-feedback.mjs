import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
const temp = await mkdtemp(join(tmpdir(), "bound-key-"));
const repo = resolve(import.meta.dirname, "..");
const code = `import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import {ReviewFeedback} from '${join(repo, "src/ReviewFeedback.tsx")}';import {ActionForm} from '${join(repo, "src/components.tsx")}';import {FEEDBACK_DISPOSITIONS} from '${join(repo, "src/reviewFeedback.ts")}';
const initial={id:'E',permissions:['learn'],reviews:[{id:'H',kind:'HUMAN',workpaper_id:'W',status:'OPEN',history:[]},{id:'A',kind:'EXPERIMENTAL_AI',status:'SUGGESTIONS_ONLY',input_digest:'a'.repeat(64),appeals:[]},{id:'P',kind:'EXPERIMENTAL_INPUT',status:'PREPARED'}],workpapers:[{id:'W',prepared_by:'LEARNER',versions:[{version:2,actor:'LEARNER'}]}]};
function Harness(){const [e,setE]=useState(initial),[id,setId]=useState('H'),[action,setAction]=useState(null),[supported,setSupported]=useState(true),[resolution,setResolution]=useState(true);window.configure=(id,allowed=true,supported=true,role='learn',independent=true)=>{setId(id);setE(x=>({...x,permissions:allowed?[role]:[]}));setSupported(supported);setResolution(independent);setAction(null)};return <><ReviewFeedback engagement={e} review={e.reviews.find(x=>x.id===id)} supported={supported} resolutionSupported={supported&&resolution} busy={false} viewerId={e.permissions[0]==='review'?'REVIEWER':'LEARNER'} onResolveHuman={payload=>setAction({title:'Resolve human review',kind:'review.resolve',initial:payload,fields:[{name:'response',label:'Resolution rationale and evidence checked',type:'textarea',required:true}]})} onRespond={payload=>setAction({title:'Record review feedback',kind:'review.resolve',initial:payload,fields:[{name:'disposition',label:'Your response',type:'select',required:true,options:FEEDBACK_DISPOSITIONS.map(x=>({value:x,label:x}))},{name:'response',label:'Response and supporting evidence',type:'textarea',required:true}]})}/>{action&&<ActionForm action={action} busy={false} onClose={()=>setAction(null)} onSubmit={async payload=>{window.sent=payload;setE(e=>({...e,reviews:e.reviews.map(r=>r.id!==payload.review_id?r:{...r,status:payload.disposition?r.status:'RESOLVED',feedback_status:payload.disposition==='human_review'?'HUMAN_REVIEW_REQUESTED':'FEEDBACK_RECORDED',latest_response_disposition:payload.disposition,[r.kind==='EXPERIMENTAL_AI'?'appeals':'history']:[...(r[r.kind==='EXPERIMENTAL_AI'?'appeals':'history']??[]),{...payload,actor:e.permissions[0]==='review'?'REVIEWER':'LEARNER',recorded_at:'2027-01-01',response_workpaper_version_digest:'d'.repeat(64)}]})}));setAction(null);return true}}/>}</>};createRoot(document.getElementById('app')).render(<Harness/>);`;
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
  const respond = page.getByRole("button", {
    name: "Record feedback",
    exact: true,
  });
  await respond.waitFor();
  await respond.focus();
  await page.keyboard.press("Enter");
  await page
    .getByLabel("Your response", { exact: true })
    .selectOption("disagree");
  await page
    .getByLabel("Response and supporting evidence", { exact: true })
    .fill("My retained source supports a different interpretation.");
  await page.getByRole("button", { name: "Save record", exact: true }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("article", { name: "Recorded response 1" }).waitFor();
  assert.equal(
    (await page.evaluate(() => window.sent)).response_workpaper_version,
    2,
  );
  assert.match(
    await page
      .getByRole("region", { name: "Recorded review feedback" })
      .innerText(),
    /Review status: open/,
  );
  await page.evaluate(() => window.configure("A"));
  await respond.click();
  await page
    .getByLabel("Your response", { exact: true })
    .selectOption("human_review");
  await page
    .getByLabel("Response and supporting evidence", { exact: true })
    .fill("Please review this suggestion.");
  await page.getByRole("button", { name: "Save record", exact: true }).click();
  await page.getByRole("article", { name: "Recorded response 1" }).waitFor();
  assert.equal(
    (await page.evaluate(() => window.sent)).input_digest,
    "a".repeat(64),
  );
  assert.match(
    await page
      .getByRole("region", { name: "Recorded review feedback" })
      .innerText(),
    /Review status: suggestions only/,
  );
  await page.evaluate(() => window.configure("P"));
  await page
    .getByText(
      "Prepared input is not a review result and cannot receive feedback.",
      { exact: true },
    )
    .waitFor();
  assert.equal(await respond.count(), 0);
  await page.evaluate(() => window.configure("H", false));
  await page
    .getByText("Current engagement permission is required to respond.", {
      exact: true,
    })
    .waitFor();
  assert.equal(await respond.count(), 0);
  await page.evaluate(() => window.configure("H", true, false));
  await page
    .getByText(
      "This server does not support feedback recorded separately from resolution.",
      { exact: true },
    )
    .waitFor();
  assert.equal(await respond.count(), 0);
  await page.evaluate(() => window.configure("H", true, true, "review", false));
  await page
    .getByRole("button", { name: "Record feedback", exact: true })
    .waitFor();
  assert.equal(
    await page
      .getByRole("button", { name: "Resolve human review", exact: true })
      .count(),
    0,
  );
  await page.evaluate(() => window.configure("H", true, true, "review"));
  const resolveReview = page.getByRole("button", {
    name: "Resolve human review",
    exact: true,
  });
  await resolveReview.waitFor();
  await resolveReview.focus();
  await page.keyboard.press("Enter");
  await page
    .getByLabel("Resolution rationale and evidence checked", { exact: true })
    .fill("Checked version 2 and the retained support; comment addressed.");
  await page.getByRole("button", { name: "Save record", exact: true }).focus();
  await page.keyboard.press("Enter");
  await page
    .getByText("Recorded reviewer resolution", { exact: true })
    .waitFor();
  assert.equal(await resolveReview.count(), 0);
  const resolved = await page.evaluate(() => window.sent);
  assert.equal("disposition" in resolved, false);
  assert.equal(resolved.response_workpaper_version, 2);
  assert.match(
    await page
      .getByRole("region", { name: "Recorded review feedback" })
      .innerText(),
    /Review status: resolved/,
  );
  await page.evaluate(() => window.configure("A", true, true, "review"));
  await page
    .getByRole("button", { name: "Record feedback", exact: true })
    .waitFor();
  assert.equal(await resolveReview.count(), 0);
  console.log(
    "Learner feedback and separate reviewer resolution: keyboard, exact pins, nonclosure and independent capability guards PASS",
  );
} finally {
  await browser.close();
  await rm(temp, { recursive: true, force: true });
}
