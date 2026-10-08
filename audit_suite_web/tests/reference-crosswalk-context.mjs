// One bounded navigation mechanism: declared metadata, no source/Key inputs.
import { mkdir, writeFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";

const out = process.env.CROSSWALK_BROWSER_OUTPUT;
const expectReset = process.env.CROSSWALK_CONTEXT_EXPECT === "reset";
assert.ok(out?.startsWith("/home/kingoftheeast/"));
await mkdir(out, { mode: 0o700 });
const repo = resolve(import.meta.dirname, "..");
const code = `import React from 'react';import {createRoot} from 'react-dom/client';
import {ReferenceCrosswalk} from '${join(repo, "src/ReferenceCrosswalk.tsx")}';
const rows=Array.from({length:51},(_,i)=>({legacy_id:'legacy-'+i,raw_sha256:'a'.repeat(64),canonical_sha256:'b'.repeat(64),key_sha256:'c'.repeat(64),relations:[{current_id:i===50?'single':'many',status:'SHARED_CONTROL_ONLY',reason:'Literal declaration only',proof:null}]}));
const value={schema:'SH_PRIVATE_INSTRUCTOR_REFERENCE_CROSSWALK_V1',projection:'DECLARED_NAVIGATION_ONLY',sha256:'d'.repeat(64),engagement_id:'OWN',archive_sha256:'e'.repeat(64),professional_acceptance:'NOT_ASSERTED',rows,current_cards:[],inverse:[]};
const root=createRoot(document.getElementById('app'));window.draw=(mode='CURRENT',selected='many',sha='d'.repeat(64))=>root.render(<ReferenceCrosswalk value={{...value,sha256:sha}} mode={mode} selected={selected}/>);window.draw();`;
await build({ stdin: { contents: code, resolveDir: repo, loader: "tsx" }, bundle: true, format: "iife", jsx: "automatic", outfile: join(out, "app.js") });
await writeFile(join(out,"index.html"),'<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="app.css"></head><body><main id="app"></main><script src="app.js"></script></body></html>',{mode:0o600});
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
const observations=[];
try {
  const page=await browser.newPage({viewport:{width:390,height:900}});
  await page.goto('file://'+join(out,'index.html'));
  const details=page.locator('details.reference-crosswalk');
  const open=async()=>{await details.locator(':scope > summary').click();};
  await open();
  await details.getByRole('button',{name:'Next reference links',exact:true}).click();
  await details.getByRole('button',{name:'Next reference links',exact:true}).click();
  await details.getByText('Page 3 of 3',{exact:true}).waitFor();
  await page.evaluate(()=>window.draw('CURRENT','single'));
  await page.waitForFunction(()=>document.querySelector('.reference-crosswalk').textContent.includes('1 reference variants match.'));
  observations.push({change:'current selection',count:await details.locator(':scope > ul > li').count(),page:await details.locator('.actions span').textContent()});
  if(expectReset){assert.equal(observations.at(-1).count,1);assert.equal(observations.at(-1).page,'Page 1 of 1');await open();}
  await details.getByLabel('Search reference links').fill('missing');
  await details.getByLabel('Relation status').selectOption('UNRESOLVED');
  await page.evaluate(()=>window.draw('ARCHIVE','legacy-50'));
  await page.waitForFunction(()=>document.querySelector('.reference-crosswalk'));
  observations.push({change:'mode and legacy selection',query:await details.getByLabel('Search reference links').inputValue(),status:await details.getByLabel('Relation status').inputValue(),count:await details.locator(':scope > ul > li').count()});
  if(expectReset){assert.equal(observations.at(-1).query,'');assert.equal(observations.at(-1).status,'all');assert.equal(observations.at(-1).count,1);await open();}
  await details.getByLabel('Search reference links').fill('missing');
  await details.getByLabel('Relation status').selectOption('OUT_OF_SCOPE');
  await page.evaluate(()=>window.draw('ARCHIVE','legacy-50','f'.repeat(64)));
  await page.waitForFunction(()=>document.querySelector('.reference-crosswalk').textContent.includes('f'.repeat(64)));
  observations.push({change:'external crosswalk pin',query:await details.getByLabel('Search reference links').inputValue(),status:await details.getByLabel('Relation status').inputValue(),count:await details.locator(':scope > ul > li').count()});
  if(expectReset){assert.equal(observations.at(-1).query,'');assert.equal(observations.at(-1).status,'all');assert.equal(observations.at(-1).count,1);}
  else {assert.equal(observations[0].count,0);assert.equal(observations[0].page,'Page 3 of 1');assert.equal(observations[1].query,'missing');assert.equal(observations[2].status,'OUT_OF_SCOPE');}
  await writeFile(join(out,'REPORT.json'),JSON.stringify({status:expectReset?'PASS_FOCUSED_CONTEXT_RESET':'REPRODUCED_STALE_CONTEXT_FILTER_AND_PAGE',declared_metadata_only:true,actual_pair_acceptance:false,observations},null,2)+'\n',{mode:0o600});
} finally {await browser.close();}
