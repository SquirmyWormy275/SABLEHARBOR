import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
const temp = await mkdtemp(join(tmpdir(), "saved-view-ui-"));
const repo = resolve(import.meta.dirname, "..");
await build({
  stdin: {
    contents: `
import React,{useState} from 'react';import{createRoot}from'react-dom/client';
import{SavedViews}from'${join(repo, "src/SavedViews.tsx")}';
import{TableWorkspace}from'${join(repo, "src/TableWorkspace.tsx")}';
import{Table}from'${join(repo, "src/components.tsx")}';
window.calls=[];window.restored=[];window.saved=[];window.scrollCapture=12;window.mode='normal';window.revision=1;
const answer=x=>new Response(JSON.stringify(x),{status:200,headers:{'Content-Type':'application/json'}});
const view=v=>({...v,engagement_id:'E',current_engagement_revision:window.revision,context_status:window.redacted?'CONTEXT_CHANGED':'CURRENT',personal_content_visible:!window.redacted&&v.status==='ACTIVE',restorable:!window.redacted&&v.status==='ACTIVE',navigation:null});
window.fetch=async(path,options={})=>{
 const method=options.method??'GET',body=options.body?JSON.parse(options.body):null;window.calls.push({path,method,body});
 if(path.endsWith('/link')){if(JSON.stringify(Object.keys(body).sort())!==JSON.stringify(['id','kind','version']))throw Error('wrong link envelope');return answer({...body,sha256:'a'.repeat(64)});}
 if(method==='GET')return answer({views:window.saved.map(view)});
 if(path.endsWith('/restore')){const response={...view(window.saved[0]),navigation:{...window.saved[0].user}};delete response.navigation.title;if(window.mode==='wrong')response.id='WRONG';if(window.mode==='delay')return new Promise(resolve=>window.finish=()=>resolve(answer(response)));return answer(response);}
 if(path.endsWith('/clear')){if(body.expected_version!==window.saved[0].version)throw Error('stale clear');window.saved[0]={...window.saved[0],status:'CLEARED',version:window.saved[0].version+1};return answer(view(window.saved[0]));}
 const expected=method==='PUT'?['command_id','expected_engagement_revision','expected_version','payload']:['command_id','expected_engagement_revision','payload'];
 if(JSON.stringify(Object.keys(body).sort())!==JSON.stringify(expected.sort()))throw Error('Wrong save envelope');
 if(JSON.stringify(Object.keys(body.payload).sort())!==JSON.stringify(['title','section','query','framework','reference','table','scroll_top'].sort()))throw Error('Unbounded payload');
 if(body.expected_engagement_revision!==window.revision)throw Error('wrong revision');
 if(method==='PUT'&&body.expected_version!==window.saved[0].version)throw Error('stale replacement');
 const saved={id:'V',version:method==='PUT'?window.saved[0].version+1:1,status:'ACTIVE',user:body.payload,saved_at:'now',engagement_revision:window.revision,revision_status:'CURRENT',target_status:'HISTORICAL_VERSION_AVAILABLE'};window.saved=[saved];return answer(view(saved));
};
const all=Array.from({length:80},(_,n)=>({id:n?'W'+n:'W',title:'Report '+String(n).padStart(3,'0'),version:2,versions:[{version:1},{version:2}]}));
function App(){const[revision,setRevision]=useState(1),[rows,setRows]=useState(all);window.advance=()=>{window.revision++;setRevision(window.revision)};window.shrink=()=>setRows(all.slice(0,2));
const e={id:'E',revision,permissions:['learn'],scope:{programs:['SOC2']},workpapers:all};
return <TableWorkspace><SavedViews engagement={e} viewerId='L' enabled={true} selectedReference={{kind:'workpaper',id:'W',version:1}} getNavigation={()=>({section:'review',query:'global',framework:'all',scroll_top:window.scrollCapture,secret:'DO NOT STORE'})} onRestore={(nav,row,opener)=>window.restored.push({nav,id:row?.id,opener:opener?.textContent,connected:opener?.isConnected})}/><Table memoryKey='workpapers' rows={rows} columns={[{key:'title',label:'Title'}]}/></TableWorkspace>}
createRoot(document.getElementById('app')).render(<App/>);`,
    resolveDir: repo,
    loader: "tsx",
  },
  resolveExtensions: [".ts", ".tsx", ".js"],
  bundle: true,
  format: "iife",
  jsx: "automatic",
  outfile: join(temp, "app.js"),
});
await writeFile(
  join(temp, "index.html"),
  '<html><body><div id="app"></div><script src="app.js"></script></body></html>',
);
const browser = await chromium.launch({
  executablePath: "/usr/bin/chromium",
  headless: true,
  args: ["--no-sandbox"],
});
try {
  const page = await browser.newPage();
  await page.goto("file://" + join(temp, "index.html"));
  await page.getByText("Personal saved views", { exact: true }).click();
  await page.getByLabel("View title").fill("Exact old workpaper");
  await page.getByLabel("Table navigation").selectOption("workpapers");
  await page.getByLabel("Include this exact record version").check();
  await page.getByLabel("Search records").fill("Report");
  await page
    .getByRole("button", { name: "Sort by Title", exact: true })
    .click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.evaluate(() => (window.scrollCapture = 777));
  await page
    .getByRole("button", { name: "Save current view", exact: true })
    .click();
  await page
    .getByText("Personal navigation saved. No audit work was changed.", {
      exact: true,
    })
    .waitFor();
  const saved = await page.evaluate(() => window.saved[0]);
  assert.equal(saved.user.scroll_top, 777);
  assert.equal(saved.user.reference.version, 1);
  assert.deepEqual(saved.user.table, {
    id: "workpapers",
    query: "Report",
    sort: "title",
    page: 2,
  });
  assert.equal(saved.user.secret, undefined);
  await page.getByLabel("Search records").fill("absent");
  await page.evaluate(() => (window.mode = "delay"));
  await page.getByRole("button", { name: "Restore view", exact: true }).click();
  await page.waitForFunction(() => typeof window.finish === "function");
  // Disabling the restore button may move browser focus to body while awaiting.
  await page.evaluate(() => { document.activeElement?.blur(); window.finish(); });
  await page.waitForFunction(() => window.restored.length === 1);
  assert.equal(await page.evaluate(() => window.restored[0].opener), "Restore view");
  assert.equal(await page.evaluate(() => window.restored[0].connected), true);
  await page.evaluate(() => (window.mode = "normal"));
  assert.equal(await page.getByLabel("Search records").inputValue(), "Report");
  await page.getByText("Page 3 of 4", { exact: true }).waitFor();
  assert.equal(
    (await page.evaluate(() => window.restored[0])).nav.reference.version,
    1,
  );
  await page.evaluate(() => window.shrink());
  await page.getByRole("button", { name: "Restore view", exact: true }).click();
  await page.getByText(/Page adjusted from 3 to 1/).waitFor();
  await page.evaluate(() => (window.mode = "wrong"));
  await page.getByRole("button", { name: "Restore view", exact: true }).click();
  await page
    .getByRole("alert")
    .filter({ hasText: "changed or is unavailable" })
    .waitFor();
  assert.equal(await page.evaluate(() => window.restored.length), 2);
  await page.evaluate(() => (window.mode = "delay"));
  await page.getByRole("button", { name: "Restore view", exact: true }).click();
  await page.waitForFunction(() => typeof window.finish === "function");
  await page.evaluate(() => window.advance());
  await page.getByLabel("View title").fill("After revision");
  await page.evaluate(() => window.finish());
  await page.waitForTimeout(50);
  assert.equal(await page.evaluate(() => window.restored.length), 2);
  await page.getByLabel("View title").fill("Updated current view");
  await page
    .getByRole("button", { name: "Replace with current view", exact: true })
    .click();
  await page.getByText("Updated current view", { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => window.saved[0].version), 2);
  await page.evaluate(() => (window.redacted = true));
  await page
    .getByRole("button", { name: "Refresh saved views", exact: true })
    .click();
  await page
    .getByText("View unavailable in the current context", { exact: true })
    .waitFor();
  assert.equal(
    await page
      .getByRole("button", { name: "Restore view", exact: true })
      .isDisabled(),
    true,
  );
  await page.getByRole("button", { name: "Clear view", exact: true }).click();
  await page.getByText("Cleared view", { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => window.saved[0].status), "CLEARED");
  console.log(
    "PASS saved-view strict nested envelope/server link, click-time scroll, historical WP1, mounted table query/sort/page restore and clamp, mismatched/late response rejection, CAS replacement, redaction and clear",
  );
} finally {
  await browser.close();
  await rm(temp, { recursive: true, force: true });
}
