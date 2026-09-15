import { mkdtemp, writeFile, rm, chmod, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
const temp = await mkdtemp(join(tmpdir(), "assistance-")),
  repo = resolve(import.meta.dirname, "..");
const code = `import React,{useState}from'react';import{createRoot}from'react-dom/client';import '${join(repo, "src/style.css")}';import{InstructorAssistance}from'${join(repo, "src/InstructorAssistance.tsx")}';import{setCSRF}from'${join(repo, "src/api.ts")}';setCSRF('fixture-csrf');window.calls=[];let preview,release=false,delivered=false,ack=false,revoked=false;window.failConfirm=true;window.fetch=async(url,init={})=>{let payload=init.body?JSON.parse(init.body):undefined;window.calls.push({url,method:init.method??'GET',payload,csrf:init.headers?.['X-CSRF-Token']});const ok=value=>new Response(JSON.stringify(value),{status:200,headers:{'Content-Type':'application/json'}});if(url.endsWith('/options'))return ok({engagement_id:'E',revision:2,recipients:[{id:'L',name:'Named learner'}],tasks:[{id:'T',title:'Inspect actual row',sha256:'a'.repeat(64)}],artifacts:[{id:'A',name:'retained.csv',sha256:'b'.repeat(64)}]});if(url.endsWith('/preview')){if(window.previewConflict){window.previewConflict=false;return new Response(JSON.stringify({error:'Preview revision changed'}),{status:409,headers:{'Content-Type':'application/json'}});}preview={id:'P'+window.calls.length,engagement_id:'E',instructor_id:'I',recipient_id:payload.recipient_id,revision:2,expires_at:new Date(Date.now()+60000).toISOString(),content:{stage:payload.stage,text:payload.text,pointers:payload.pointers}};return ok({preview,preview_sha256:'c'.repeat(64),delivered:false});}if(url.endsWith('/instructor-releases')&&init.method==='POST'){if(window.failConfirm){window.failConfirm=false;throw Error('Simulated lost response; retry exact confirmation');}release=true;return ok({status:'RELEASED',delivered:false});}if(url.endsWith('/revoke')){revoked=true;return ok({status:'REVOKED'});}if(url.endsWith('/acknowledge')){ack=true;return ok({status:'ACKNOWLEDGED'});}if(url.endsWith('/assistance/R')){if(window.deferRead)await new Promise(resolve=>window.finishRead=resolve);delivered=true;return ok({release_id:'R',release_sha256:'d'.repeat(64),content:preview.content,pre_release_revision:2,understanding:'NOT_INFERRED'});}if(url.endsWith('/assistance')||url.endsWith('/instructor-releases'))return ok(release?[{release_id:'R',recipient_id:'L',stage:'HINT',status:revoked?'REVOKED':'RELEASED',delivered,acknowledged:ack}]:[]);throw Error('unexpected route '+url)};function App(){const[actor,setActor]=useState('I'),[supported,setSupported]=useState(true);window.viewer=(id,cap=true)=>{setActor(id);setSupported(cap)};const mode=actor==='I'?'instructor':'learner';return <main className='workspace'><InstructorAssistance engagement={{id:'E',revision:2,permissions:actor==='I'?['instruct']:['learn'],scope:{},tasks:[{id:'T'}],artifacts:[],sample_execution_inputs:{engagement_id:'E',engagement_revision:2,tasks:[{task_id:'T',task_digest:'a'.repeat(64)}]}}} onReloadContext={async()=>{window.reloaded=true}} onOpenPointer={p=>window.pointerOpened=p} viewerId={actor} supported={supported} mode={mode}/></main>};createRoot(document.getElementById('app')).render(<App/>);`;
await build({
  stdin: { contents: code, resolveDir: repo, loader: "tsx" },
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
  await page
    .getByLabel("Named assistance recipient", { exact: true })
    .selectOption("L");
  await page
    .getByLabel("Exact assistance message")
    .fill("Consider the independent reconciliation.");
  await page.evaluate(() => (window.previewConflict = true));
  await page.getByRole("button", { name: "Preview exact assistance" }).click();
  await page
    .getByRole("button", { name: "Reload engagement context" })
    .waitFor();
  await page
    .getByRole("button", { name: "Refresh assistance history" })
    .click();
  await page.getByRole("button", { name: "Reload engagement context" }).click();
  await page
    .getByLabel("Named assistance recipient", { exact: true })
    .waitFor();
  assert.equal(await page.evaluate(() => window.reloaded), true);
  await page.getByRole("button", { name: "Preview exact assistance" }).click();
  await page
    .getByRole("region", { name: "Exact assistance preview" })
    .waitFor();
  assert.equal(
    (await page.evaluate(() => window.calls)).filter(
      (c) => c.method === "POST" && !c.url.endsWith("/preview"),
    ).length,
    0,
  );
  await page
    .getByLabel("Exact assistance message")
    .fill("Edited explicit guidance.");
  assert.equal(
    await page
      .getByRole("region", { name: "Exact assistance preview" })
      .count(),
    0,
  );
  await page
    .getByLabel("Assistance stage", { exact: true })
    .selectOption("POINTER");
  await page
    .getByLabel("Exact assistance pointer", { exact: true })
    .selectOption("T");
  await page
    .getByRole("button", { name: "Add exact pointer", exact: true })
    .click();
  await page.getByRole("button", { name: "Preview exact assistance" }).click();
  await page
    .getByRole("region", { name: "Exact assistance preview" })
    .waitFor();
  if (process.env.AUDIT_UI_CAPTURE_ROOT) {
    for (const width of [1400, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve)),
          ),
      );
      const path = join(
        process.env.AUDIT_UI_CAPTURE_ROOT,
        "assistance-preview-" + width + ".png",
      );
      await page.screenshot({ path, fullPage: true });
      await chmod(path, 0o600);
    }
  }
  await page
    .getByRole("button", { name: "Confirm release to named learner" })
    .focus();
  await page.keyboard.press("Enter");
  await page
    .getByRole("alert")
    .filter({ hasText: "Simulated lost response" })
    .waitFor();
  await page
    .getByRole("button", { name: "Confirm release to named learner" })
    .click();
  await page.getByRole("button", { name: "Revoke assistance R" }).waitFor();
  const confirms = (await page.evaluate(() => window.calls)).filter(
    (c) => c.url.endsWith("/instructor-releases") && c.method === "POST",
  );
  assert.equal(confirms.length, 2);
  assert.equal(confirms[0].payload.command_id, confirms[1].payload.command_id);
  assert.equal(confirms[0].csrf, "fixture-csrf");
  await page.evaluate(() => window.viewer("L"));
  await page.getByRole("button", { name: "Open assistance R" }).waitFor();
  assert.equal(
    (await page.evaluate(() => window.calls)).filter((c) =>
      c.url.endsWith("/assistance/R"),
    ).length,
    0,
  );
  assert.equal(
    await page.getByText("Edited explicit guidance.", { exact: true }).count(),
    0,
  );
  await page.getByRole("button", { name: "Open assistance R" }).click();
  await page
    .getByRole("region", { name: "Opened instructor assistance" })
    .waitFor();
  await page
    .getByRole("button", { name: "Acknowledge opened assistance" })
    .click();
  await page
    .getByRole("status")
    .filter({ hasText: "Acknowledgment recorded" })
    .waitFor();
  await page.getByRole("button", { name: "Hide assistance content" }).click();
  await page.evaluate(() => {
    window.deferRead = true;
  });
  await page.getByRole("button", { name: "Open assistance R" }).click();
  await page.waitForFunction(() => !!window.finishRead);
  await page.evaluate(() => {
    window.viewer("OTHER");
    window.finishRead();
  });
  await page
    .getByRole("heading", { name: "My instructor assistance" })
    .waitFor();
  assert.equal(
    await page
      .getByRole("region", { name: "Opened instructor assistance" })
      .count(),
    0,
  );
  await page.evaluate(() => window.viewer("I"));
  await page.getByRole("button", { name: "Revoke assistance R" }).click();
  await page.getByLabel("Revocation reason").fill("Incorrect release target.");
  await page.getByRole("button", { name: "Confirm revocation" }).click();
  await page.getByRole("status").filter({ hasText: "Revoked." }).waitFor();
  await page.evaluate(() => window.viewer("L"));
  await page.getByText(/REVOKED/).waitFor();
  assert.equal(
    await page.getByRole("button", { name: "Open assistance R" }).count(),
    0,
  );
  await page.evaluate(() => window.viewer("L", false));
  await page.waitForFunction(
    () => !document.querySelector(".instructor-assistance"),
  );
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  console.log(
    "PASS explicit preview/edit invalidation, exact pointer+CSRF, same-command retry, learner no-auto-open, acknowledge/revoke, late actor response rejection, legacy capability and styled narrow layout",
  );
} finally {
  await browser.close();
  await rm(temp, { recursive: true, force: true });
}
