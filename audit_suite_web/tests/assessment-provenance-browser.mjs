import { chromium } from "@playwright/test";
import { createServer } from "vite";
import { writeFile } from "node:fs/promises";
import assert from "node:assert/strict";
const output=process.env.ASSESSMENT_TEST_OUTPUT;if(!output)throw Error("Explicit private neutral output required");
const formats=process.env.ASSESSMENT_PARENT_CONTROL === "1" ? ["V2_GRAPH"] : ["V1","V2_GRAPH","V2_RAW"];
const cases=[],evidence=[];let server,browser,currentCase;
const xml=(fail=null)=>`<?xml version="1.0"?><testsuite name="actual neutral assessment provenance component" tests="${cases.length+(fail?1:0)}" failures="${fail?1:0}" errors="0">${cases.map(x=>`<testcase name="${x.format} save and reopen full assessment" time="${x.seconds}"/>`).join("")}${fail?`<testcase name="${currentCase} save and reopen full assessment"><failure message="actual render/assertion failure"/></testcase>`:""}</testsuite>\n`;
try{
 server=await createServer({configFile:"vite.assessment-fixture.config.ts"});await server.listen();const base=`http://127.0.0.1:${server.httpServer.address().port}`;
 browser=await chromium.launch({headless:true,executablePath:"/usr/bin/chromium"});
 for(const format of formats){
  currentCase=format;const started=Date.now();const page=await browser.newPage();page.setDefaultTimeout(5000);const errors=[],calls=[];let record;
  page.on("pageerror",e=>errors.push(e.message));
  await page.route("**/api/**",async route=>{
   const req=route.request(),path=new URL(req.url()).pathname;const {props,reference}=await page.evaluate(()=>window.neutralFixture);
   const options={engagement_id:props.engagement.id,current_engagement_revision:3,learner_revision:1,key_pin:"a".repeat(64),rubric_sha256:"a".repeat(64),inventory_sha256:"a".repeat(64),selected_state_sha256:"a".repeat(64),selected_history_tip_sha256:"c".repeat(64),audited_actor_id:"NEUTRAL-AUDITOR",bound_revision:0,issues:[{id:"NEUTRAL-I",claim:"Neutral authored interpretation",control_ids:[],uncertainty:"UNVALIDATED"}],expectations:[{id:"NEUTRAL-X",issue_ids:["NEUTRAL-I"],procedure:"Neutral expected procedure",acceptable_alternatives:[]}],references:[],...(format === "V1" ? {selected_history_sha256:"e".repeat(64)} : {history_integrity_format:"SELECTED_HISTORY_INTEGRITY_REFERENCE_V2",selected_history_integrity_reference:reference})};
   calls.push({method:req.method(),path});let value;
   if(req.method()==="GET" && path.endsWith("/options"))value=options;
   else if(req.method()==="POST" && path.endsWith("/instructor-assessments")){
    const payload=req.postDataJSON();assert.equal(payload.title,"Neutral authored "+format);assert.equal(payload.dimensions.length,6);assert(payload.dimensions.every(d=>d.assessment && d.rationale));
    const {command_id,expected_engagement_revision,learner_revision,key_pin,rubric_sha256,inventory_sha256,predecessor,...authored}=payload;
    record={id:"NEUTRAL-ASSESSMENT",engagement_id:props.engagement.id,version:1,sha256:"9".repeat(64),predecessor,saved_engagement_revision:3,current_engagement_revision:3,learner_revision,context_status:"CURRENT",personal_content_visible:true,correction_allowed:true,title:authored.title,document:{schema:format === "V1" ? "INSTRUCTOR_AUTHORED_ASSESSMENT_V1" : "INSTRUCTOR_AUTHORED_ASSESSMENT_V2",id:"NEUTRAL-ASSESSMENT",version:1,actor_id:props.viewerId,engagement_id:props.engagement.id,recorded_at:"2026-10-07T00:00:00Z",predecessor,pins:{key_pin,rubric_sha256,inventory_sha256,audited_actor_id:"NEUTRAL-AUDITOR",learner_revision,selected_state_sha256:"a".repeat(64),selected_history_tip_sha256:"c".repeat(64),bound_revision:0,...(format === "V1" ? {selected_history_sha256:"e".repeat(64)} : {selected_history_integrity_reference:reference})},authored,selected_issues:options.issues,selected_expectations:options.expectations,references:[],qualification:"INSTRUCTOR_AUTHORED_UNVALIDATED_NO_AGGREGATE_GRADE_SHARED_STATE_NOT_SUBMISSION"}};value=record;
   }else if(req.method()==="GET" && path.endsWith("/NEUTRAL-ASSESSMENT")){assert(record);value=record;}
   else throw Error("Unexpected neutral request "+req.method()+" "+path);
   await route.fulfill({json:value});
  });
  await page.goto(base+"/tests/assessment-provenance.html?format="+format);
  await page.getByText("Instructor assessment of this recorded work",{exact:true}).click();
  await page.getByRole("button",{name:"Load exact assessment choices"}).click();
  await page.getByLabel("Assessment title",{exact:true}).fill("Neutral authored "+format);
  await page.getByLabel("Assessment issues",{exact:true}).selectOption("NEUTRAL-I");
  await page.getByLabel("Assessment expectations",{exact:true}).selectOption("NEUTRAL-X");
  for(const d of ["discovery","evidence","testing","judgment","documentation","follow-through"]){await page.getByLabel(d+" assessment",{exact:true}).fill("Not assessed: "+d);await page.getByLabel(d+" rationale",{exact:true}).fill("Neutral independent evaluation required: "+d);}
  await page.getByRole("button",{name:"Save instructor assessment",exact:true}).click();
  await page.getByRole("region",{name:"Opened instructor assessment"}).waitFor();
  assert.equal(await page.getByRole("heading",{name:"Neutral workroom summary",exact:true}).count(),1);assert.deepEqual(errors,[]);assert.equal(calls.filter(c=>c.method==="POST").length,1);
  await page.getByText("Exact assessment provenance",{exact:true}).click();
  const opened=page.getByRole("region",{name:"Opened instructor assessment"});
  if(format === "V1"){assert.equal(await opened.getByText("selected_history_sha256: "+"e".repeat(64),{exact:true}).count(),1);assert.equal(await opened.getByRole("region",{name:"Selected history integrity reference"}).count(),0);}
  else{const ref=opened.getByRole("region",{name:"Selected history integrity reference"});assert.equal(await ref.locator("dt").count(),13);const {reference}=await page.evaluate(()=>window.neutralFixture);for(const [key,value] of Object.entries(reference)){const row=ref.locator("div").filter({has:page.locator("dt",{hasText:new RegExp("^"+key.replaceAll("_"," ")+"$")})});assert.equal(await row.locator("dd").textContent(),value===null ? "Not applicable (raw canonical JSON)" : String(value));}assert.equal(await opened.getByText(/selected_history_sha256:/).count(),0);}
  await page.getByRole("button",{name:"Hide assessment document"}).click();await page.getByRole("button",{name:"Open assessment NEUTRAL-ASSESSMENT",exact:true}).click();await opened.waitFor();assert.equal(await page.getByRole("heading",{name:"Neutral workroom summary",exact:true}).count(),1);assert.deepEqual(errors,[]);assert(calls.some(c=>c.path.endsWith("/NEUTRAL-ASSESSMENT") && c.method==="GET"));
  cases.push({format,seconds:(Date.now()-started)/1000});evidence.push({format,calls,errors,real_component:true,neutral_mocked_API_only:true});console.log("PASS",format,"save/reopen actual component");await page.close();
 }
 await writeFile(output+"/RESULT.json",JSON.stringify({cases,evidence,live_Main_changed:false,real_domain_commands:false},null,2)+"\n");await writeFile(output+"/TESTS.xml",xml());
}catch(error){await writeFile(output+"/FAILURE.json",JSON.stringify({error:String(error),currentCase,cases,evidence,neutral_only:true},null,2)+"\n");await writeFile(output+"/TESTS.xml",xml(error));throw error;}
finally{if(browser)await browser.close();if(server)await server.close();}
