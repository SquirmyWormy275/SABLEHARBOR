import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { build } from "esbuild";
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
const temp = await mkdtemp(join(tmpdir(), "passage-anchor-"));
const repo = resolve(import.meta.dirname, "..");
await build({
  stdin: {
    contents: `import React,{useState} from 'react';import{createRoot}from'react-dom/client';import{WorkpaperReviewAction,ReviewPassageAnchor}from'${join(repo, "src/WorkpaperPassageAnchor.tsx")}';function App(){const[v,setV]=useState({version:1,text:'A😀 repeat repeat'}),[supported,setSupported]=useState(true);window.change=(text,version=2,supported=true)=>{setV({text,version});setSupported(supported)};return <><WorkpaperReviewAction version={v} supported={supported} onReview={anchor=>window.sent=anchor??null}/><ReviewPassageAnchor review={{workpaper_version:1,workpaper_version_digest:'a'.repeat(64),anchor:{field:'text',start:1,end:2,excerpt:'😀',offset_unit:'UNICODE_CODEPOINT'}}}/></>};createRoot(document.getElementById('app')).render(<App/>);`,
    resolveDir: repo,
    loader: "tsx",
  },
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
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
try {
  await page.goto("file://" + join(temp, "index.html"));
  const open = () =>
    page.getByText("Attach exact passage (optional)", { exact: true }).click();
  await open();
  const area = page.getByLabel("Select passage in retained text");
  await area.evaluate((el) => {
    el.focus();
    el.setSelectionRange(1, 3);
  });
  await page.getByRole("button", { name: "Use selected passage" }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Review version 1" }).click();
  assert.deepEqual(await page.evaluate(() => window.sent), {
    field: "text",
    start: 1,
    end: 2,
    excerpt: "😀",
  });
  await page.evaluate(() => window.change("A😀 repeat repeat"));
  await page.getByRole("button", { name: "Review version 2" }).click();
  assert.equal(await page.evaluate(() => window.sent), null);
  assert.equal(
    await page
      .getByRole("region", { name: "Recorded review passage" })
      .locator("blockquote")
      .textContent(),
    "😀",
  );
  await page.evaluate(() => window.change("A\r\n😀 repeat", 3));
  await open();
  assert.equal(await area.inputValue(), "A\n😀 repeat");
  await area.evaluate((el) => el.setSelectionRange(2, 4));
  await page.getByRole("button", { name: "Use selected passage" }).click();
  await page
    .getByRole("alert")
    .filter({ hasText: "Carriage-return" })
    .waitFor();
  await page.getByRole("button", { name: "Review version 3" }).click();
  assert.equal(await page.evaluate(() => window.sent), null);
  await page.evaluate(() => window.change("A😀", 4, false));
  await page.getByRole("button", { name: "Review version 4" }).waitFor();
  assert.equal(
    await page
      .getByText("Attach exact passage (optional)", { exact: true })
      .count(),
    0,
  );
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
    true,
  );
  console.log(
    "PASS keyboard emoji selection, exact historical excerpt, version reset, CRLF normalization denial, legacy capability and narrow layout",
  );
} finally {
  await browser.close();
  await rm(temp, { recursive: true, force: true });
}
