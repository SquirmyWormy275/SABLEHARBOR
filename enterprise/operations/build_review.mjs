// Author the reviewed XLSX using the documented Codex artifact-tool runtime.
// Usage: builder.mjs generated/review_inputs.json publications preview-directory
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const [inputPath, outputDir, previewDir] = process.argv.slice(2);
if (!inputPath || !outputDir || !previewDir) throw new Error('Input, output and preview paths required');
const input = JSON.parse(await fs.readFile(inputPath, 'utf8'));
const workbook = Workbook.create();
const summary = workbook.worksheets.add('Results');
for (const name of Object.keys(input.tables)) workbook.worksheets.add(name);
const navy = '#173A53';
const numberFormat = '#,##0;(#,##0);"-"';
const checkFormat = '0.00;(0.00);0.00';
const letter = n => n < 26 ? String.fromCharCode(65+n) : letter(Math.floor(n/26)-1)+letter(n%26);
const labels = {
  unit:'Business', scenario:'Scenario', year:'Year', revenue_usd:'Revenue', expense_usd:'Expenses',
  net_income_usd:'Net income', assets_usd:'Assets', liabilities_usd:'Liabilities', equity_usd:'Equity',
  ending_cash_usd:'Ending cash', cash_flow:'Cash-flow class', opening_unpaid_usd:'Opening unpaid',
  requested_usd:'Payment requests', funded_usd:'Initially funded', arrears_settled_usd:'Arrears settled',
  closing_unpaid_usd:'Closing unpaid', opening_arr_usd:'Opening ARR', new_arr_usd:'New ARR',
  expansion_arr_usd:'Expansion', price_escalation_arr_usd:'Price changes', contraction_arr_usd:'Contraction',
  churn_arr_usd:'Churn', closing_arr_usd:'Closing ARR', control:'Control', scheduled:'Scheduled',
  passed:'Passed', failed:'Failed', not_run:'Not run', revision:'Revision', metric:'Measure',
  prior_usd:'Prior forecast', revised_usd:'Revised forecast', price_contribution_usd:'Price',
  volume_contribution_usd:'Volume', timing_contribution_usd:'Timing', workforce_contribution_usd:'Workforce'
};
const formulas = {
  'Cash obligations': r => `=D${r}+E${r}-F${r}-G${r}-H${r}`,
  'Customer ARR': r => `=D${r}+E${r}+F${r}+G${r}-H${r}-I${r}-J${r}`,
  'Control reviews': r => `=D${r}-SUM(E${r}:G${r})`,
  'Forecast review': r => `=G${r}-F${r}-SUM(H${r}:K${r})`
};
const dimensions = {};
function title(sheet, text, end, rows) {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${end}${rows}`).format.font = {name:'Arial',size:10,color:'#18242E'};
  sheet.getRange(`A1:${end}${rows}`).format.rowHeight = 19;
  sheet.getRange(`A2:${end}2`).format.rowHeight = 26;
  sheet.getRange('A2').values = [[text]];
  sheet.getRange('A2').format.font = {name:'Arial',size:15,bold:true,color:navy};
  sheet.getRange(`A2:${end}2`).format.borders = {bottom:{style:'thin',color:navy}};
}
for (const [name, rows] of Object.entries(input.tables)) {
  const sheet = workbook.worksheets.getItem(name);
  const fields = input.columns[name];
  const hasCheck = name !== 'Financial source';
  const last = letter(fields.length - 1 + (hasCheck ? 1 : 0));
  title(sheet, name === 'Control reviews' ? 'Control reviews: synthetic exercises' : `${name} (USD)`, last, rows.length+5);
  sheet.getRange('A3').values = [[name==='Financial source'
    ? '2026 retained calibration; 2027–2031 conditional scenarios. Source: integrated unit statements.'
    : 'Source: versioned synthetic operating records. Full populations are in the accompanying CSV and SQLite files.']];
  sheet.getRange('A3').format.font = {name:'Arial',size:10,italic:true,color:'#52606B'};
  sheet.getRange('A4').values = [[`Content: ${input.content_id}`]];
  sheet.getRange('A4').format.font = {name:'Arial',size:9,color:'#52606B'};
  sheet.getRange(`A5:${last}5`).values = [[...fields.map(k=>labels[k]||k),...(hasCheck?['Difference']:[])]];
  sheet.getRange(`A5:${last}5`).format = {fill:navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:36};
  const values = rows.map(row=>fields.map(key=>key.endsWith('_usd') ? Number(row[key]) : row[key]));
  sheet.getRange(`A6:${letter(fields.length-1)}${rows.length+5}`).values = values;
  fields.forEach((key,c)=> {
    const col = letter(c);
    sheet.getRange(`${col}5:${col}${rows.length+5}`).format.columnWidth = key==='unit'?31:key==='revision'?30:key==='metric'?23:key==='control'?24:key==='cash_flow'?20:key==='year'?9:17;
    if (key.endsWith('_usd')) sheet.getRange(`${col}6:${col}${rows.length+5}`).setNumberFormat(numberFormat);
    if (key==='year' || typeof rows[0][key]==='number') sheet.getRange(`${col}6:${col}${rows.length+5}`).setNumberFormat('0');
  });
  if (hasCheck) {
    sheet.getRange(`${last}6:${last}${rows.length+5}`).formulas = rows.map((_,i)=>[formulas[name](i+6)]);
    sheet.getRange(`${last}6:${last}${rows.length+5}`).setNumberFormat(checkFormat);
    sheet.getRange(`${last}5:${last}${rows.length+5}`).format.columnWidth = 14;
    sheet.getRange(`${last}6:${last}${rows.length+5}`).conditionalFormats.addCustom(`ABS(${last}6)>0.0001`,{fill:'#FCE4E4',font:{color:'#A32020',bold:true}});
  }
  if (name==='Control reviews') {
    sheet.getRange(`F6:G${rows.length+5}`).conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0,format:{fill:'#FFF0D1',font:{color:'#8A4B00'}}});
  }
  sheet.freezePanes.freezeRows(5);
  dimensions[name]={lastColumn:last,rows:rows.length+5};
}
summary.showGridLines=false;
summary.tabColor=navy;
const annual=input.tables['Financial source'];
const year=2027;
const display=annual.filter(r=>Number(r.year)===year).sort((a,b)=>a.unit.localeCompare(b.unit)||a.scenario.localeCompare(b.scenario));
summary.getRange(`A1:H${display.length+7}`).format.font={name:'Arial',size:10,color:'#18242E'};
summary.getRange(`A1:H${display.length+7}`).format.rowHeight=22;
summary.getRange('A1:B40').format.columnWidth=3;
summary.getRange(`C1:C${display.length+7}`).format.columnWidth=34;
summary.getRange(`D1:D${display.length+7}`).format.columnWidth=13;
summary.getRange(`E1:H${display.length+7}`).format.columnWidth=18;
summary.getRange('C2').values=[['Sable Harbor operating review']];
summary.getRange('C2').format.font={name:'Arial',size:16,bold:true,color:navy};
summary.getRange('C2:H2').format.borders={bottom:{style:'thin',color:navy}};
summary.getRange('C3:D3').values=[['Report year',year]];
summary.getRange('D3').format={fill:'#FFF0D1',font:{name:'Arial',size:10,color:'#0000FF'},horizontalAlignment:'center'};
summary.getRange('D3').dataValidation={rule:{type:'whole',operator:'between',formula1:2026,formula2:2031}};
summary.getRange('C4').values=[['Synthetic scenarios, USD. Unit cash allocations are not bank balances. Change year to select results.']];
summary.getRange('C4').format.font={name:'Arial',size:10,italic:true,color:'#52606B'};
summary.getRange('C5:H5').values=[['Business','Scenario','Revenue','Expenses','Net income','Ending cash']];
summary.getRange('C5:H5').format={fill:navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',rowHeight:28};
const end=annual.length+5;
for(let i=0;i<display.length;i++) {
  const r=i+6;
  summary.getRange(`C${r}:D${r}`).values=[[display[i].unit,display[i].scenario]];
  summary.getRange(`E${r}:H${r}`).formulas=[['D','E','F','J'].map(col=>`=SUMIFS('Financial source'!$${col}$6:$${col}$${end},'Financial source'!$A$6:$A$${end},$C${r},'Financial source'!$B$6:$B$${end},$D${r},'Financial source'!$C$6:$C$${end},$D$3)`)];
  if(i%3===0) summary.getRange(`C${r}:H${r}`).format.borders={top:{style:'thin',color:'#D2DBE1'}};
}
summary.getRange(`E6:H${display.length+5}`).setNumberFormat(numberFormat);
summary.freezePanes.freezeRows(5);
dimensions.Results={lastColumn:'H',rows:display.length+5};
// Test the year selector against an independently selected source value, then restore.
summary.getRange('D3').values=[[2028]];
workbook.recalculate();
const expected=annual.find(r=>Number(r.year)===2028&&r.unit===display[0].unit&&r.scenario===display[0].scenario);
if(Math.abs(Number(summary.getRange('E6').values[0][0])-Number(expected.revenue_usd))>0.0001) throw new Error('Report-year recalculation failed');
summary.getRange('D3').values=[[year]];
workbook.recalculate();
console.log((await workbook.inspect({kind:'table',range:'Results!C3:H12',include:'values,formulas',tableMaxRows:10,tableMaxCols:6,maxChars:2500})).ndjson);
console.log((await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:1500})).ndjson);
await fs.mkdir(outputDir,{recursive:true});
await fs.mkdir(previewDir,{recursive:true});
for (const [name, dim] of Object.entries(dimensions)) {
  const preview=await workbook.render({sheetName:name,range:`A1:${dim.lastColumn}${Math.min(dim.rows,18)}`,scale:1.3,format:'png'});
  await fs.writeFile(path.join(previewDir,`${name.replaceAll(' ','_')}.png`),new Uint8Array(await preview.arrayBuffer()));
}
const output=await SpreadsheetFile.exportXlsx(workbook);
const bookPath=path.join(outputDir,'operating-review-v1.0.0.xlsx');
await output.save(bookPath);
const digest=crypto.createHash('sha256').update(await fs.readFile(bookPath)).digest('hex');
await fs.writeFile(path.join(outputDir,'review_manifest.json'),JSON.stringify({content_id:input.content_id,workbook_sha256:digest,classification:input.classification,authoring:'Artifact Tool',verification:'Full source-cell and formula-result verification is required on every release build.'},null,2)+'\n');
console.log(JSON.stringify({workbook:bookPath,content_id:input.content_id,sha256:digest}));
