import { chromium } from "@playwright/test";
import { createServer } from "vite";
import { writeFile } from "node:fs/promises";
import assert from "node:assert/strict";
import { setTimeout as delay } from "node:timers/promises";
const output = process.env.OPTIONAL_TEST_OUTPUT;
if (!output) throw Error("Explicit private neutral output required");
const cases = []; let browser, server;
async function test(name, fn) { const start = Date.now(); await fn(); cases.push({ name, seconds: (Date.now()-start)/1000 }); console.log("PASS", name); }
const counts = {}; let pending = null, failContexts = false;
try {
  server = await createServer({ configFile: "vite.optional-fixture.config.ts" }); await server.listen();
  const base = `http://127.0.0.1:${server.httpServer.address().port}`;
  browser = await chromium.launch({ headless: true, executablePath: "/usr/bin/chromium" });
  const page = await browser.newPage(); const pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await page.route("**/api/**", async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    counts[path] = (counts[path] || 0) + 1;
    if (request.method() !== "GET") throw Error("No mutation permitted in this fixture");
    const state = await page.evaluate(() => window.getFixture());
    if (path.endsWith("/contexts") && pending) { const saved=pending; pending=null; await saved.promise; await route.fulfill({ status:500, json:{ error:"obsolete neutral failure" } }); return; }
    if (path.endsWith("/contexts") && failContexts) { await route.fulfill({ status:500, json:{ error:"neutral current failure" } }); return; }
    let body;
    if (path.endsWith("/saved-views")) body={ views:[] };
    else if (path.endsWith("/contexts")) body={ contexts:[] };
    else if (path.endsWith("/handoffs/members")) body={ engagement_id:state.id, engagement_revision:state.revision, members:[] };
    else if (path.endsWith("/handoffs")) body={ handoffs:[] };
    else if (path.endsWith("/visit-checkpoint")) body={ engagement_id:state.id, current_engagement_revision:state.revision, version:0, status:"NO_CHECKPOINT", formal_work_mutated:false, supported_kinds:[] };
    else if (path.endsWith("/jobs")) body={ jobs:[{ id:"NEUTRAL-JOB", status:"PENDING", kind:"company.census.collect", expected_revision:1, attempts:0, result_revision:null }] };
    else throw Error("Unexpected neutral API path "+path);
    await route.fulfill({ json:body });
  });
  await page.goto(base+"/tests/optional-panels.html");
  const summary = text => page.locator("summary").filter({ hasText:new RegExp("^"+text+"$") });
  const panel = text => summary(text).locator("..");
  const open = async text => { const s=summary(text); if (!(await panel(text).evaluate(el=>el.open))) await s.click(); };
  const close = async text => { if (await panel(text).evaluate(el=>el.open)) await summary(text).click(); };
  const count = suffix => Object.entries(counts).filter(([p])=>p.endsWith(suffix)).reduce((n,[,v])=>n+v,0);
  async function waitCount(suffix,n) { for (let i=0;i<200;i++) { if(count(suffix)>=n)return; await delay(20); } throw Error("Missing expected request "+suffix+" "+JSON.stringify(counts)); }
  await summary("Personal saved views").waitFor(); await delay(180);
  await test("collapsed optional panels issue zero requests", async()=>{ assert.equal(count("/saved-views"),0);assert.equal(count("/contexts"),0);assert.equal(count("/handoffs"),0);assert.equal(count("/handoffs/members"),0);assert.equal(count("/visit-checkpoint"),0); });
  await test("native keyboard open starts one saved-view listing", async()=>{ await summary("Personal saved views").focus();await page.keyboard.press("Enter");await waitCount("/saved-views",1);assert.equal(count("/saved-views"),1); });
  await test("closing saved views preserves text and reopening avoids duplicate mount", async()=>{ await panel("Personal saved views").getByLabel("View title").fill("neutral unsaved title");await close("Personal saved views");await open("Personal saved views");assert.equal(await panel("Personal saved views").getByLabel("View title").inputValue(),"neutral unsaved title");assert.equal(count("/saved-views"),1); });
  await test("contexts load once opened and retain edits while collapsed", async()=>{ await open("Saved investigations");await waitCount("/contexts",1);await panel("Saved investigations").getByLabel("Investigation title").fill("neutral question draft");await close("Saved investigations");await page.evaluate(()=>window.changeFixture({revision:2}));await delay(120);assert.equal(count("/contexts"),1);await open("Saved investigations");await waitCount("/contexts",2);assert.equal(await panel("Saved investigations").getByLabel("Investigation title").inputValue(),"neutral question draft"); });
  await test("handoff directory and list only refresh when visible", async()=>{ await open("Share an investigation");await waitCount("/handoffs",1);await waitCount("/handoffs/members",1);await panel("Share an investigation").getByLabel("Investigation title").fill("neutral handoff draft");await close("Share an investigation");await page.evaluate(()=>window.changeFixture({revision:3}));await delay(120);assert.equal(count("/handoffs"),1);assert.equal(count("/handoffs/members"),1);await open("Share an investigation");await waitCount("/handoffs",2);assert.equal(await panel("Share an investigation").getByLabel("Investigation title").inputValue(),"neutral handoff draft"); });
  await test("actual company context resets activation without stale listing", async()=>{ await page.evaluate(()=>window.changeFixture({company_source_binding:{branch:"neutral-b"}}));await delay(120);for(const text of ["Personal saved views","Saved investigations","Share an investigation"])assert.equal(await panel(text).evaluate(el=>el.open),false);const before=count("/saved-views");await open("Personal saved views");await waitCount("/saved-views",before+1);assert.equal(await panel("Personal saved views").getByLabel("View title").inputValue(),""); });
  await test("current listing failure stays explicit without automatic retries", async()=>{ failContexts=true;await open("Saved investigations");await panel("Saved investigations").getByRole("alert").filter({hasText:"neutral current failure"}).waitFor();const n=count("/contexts");await delay(140);assert.equal(count("/contexts"),n);await close("Saved investigations");failContexts=false; });
  await test("obsolete context failure cannot publish into replacement context", async()=>{ await page.evaluate(()=>window.changeFixture({company_source_binding:{branch:"neutral-c"}}));await delay(100);let release;pending={promise:new Promise(r=>release=r)};await open("Saved investigations");for(let i=0;i<100 && pending;i++)await delay(20);assert.equal(pending,null,"old-context request must really start");await page.evaluate(()=>window.changeFixture({company_source_binding:{branch:"neutral-d"}}));await delay(100);release();await open("Saved investigations");await delay(140);assert.equal(await page.getByText("obsolete neutral failure").count(),0); });
  await test("checkpoint remains explicit user-triggered and no collapsed fetch", async()=>{ assert.equal(count("/visit-checkpoint"),0);await open("Changes since my checkpoint");await delay(100);assert.equal(count("/visit-checkpoint"),0);await panel("Changes since my checkpoint").getByRole("button",{name:"Refresh my checkpoint"}).click();await waitCount("/visit-checkpoint",1);assert.equal(count("/visit-checkpoint"),1); });
  await test("collapsed active background-job monitoring remains live", async()=>{ const n=count("/jobs");assert(n>=1);await waitCount("/jobs",n+1);assert.equal(await panel("Background work fixture").evaluate(el=>el.open),false); });
  await test("permission context reset withholds optional reads", async()=>{ await page.evaluate(()=>window.changeFixture({permissions:[]}));await delay(100);const n=count("/contexts");await open("Saved investigations");await delay(120);assert.equal(count("/contexts"),n);assert.equal(await summary("Personal saved views").count(),0);assert.equal(await summary("Share an investigation").count(),0); });
  assert.deepEqual(pageErrors,[]);await writeFile(output+"/RESULT.json",JSON.stringify({cases,counts,pageErrors,neutral_only:true,live_Main_or_SQL_or_world:false},null,2)+"\n");
} catch(error) { await writeFile(output+"/FAILURE.json",JSON.stringify({error:String(error),cases,counts,neutral_only:true},null,2)+"\n");throw error; }
finally { if(browser)await browser.close();if(server)await server.close(); }
const escaped=v=>v.replaceAll("&","&amp;").replaceAll('"',"&quot;").replaceAll("<","&lt;");
await writeFile(output+"/TESTS.xml",`<?xml version="1.0"?><testsuite name="neutral optional panel component browser" tests="${cases.length}" failures="0" errors="0">${cases.map(x=>`<testcase name="${escaped(x.name)}" time="${x.seconds}"/>`).join("")}</testsuite>\n`);
