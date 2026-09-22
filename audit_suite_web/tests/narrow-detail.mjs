import { chromium } from "@playwright/test";
import { readFile } from "node:fs/promises";
import assert from "node:assert/strict";

const css = await readFile(
  process.argv[2] || new URL("../src/style.css", import.meta.url),
  "utf8",
);
const browser = await chromium.launch({
  headless: true,
  executablePath: "/usr/bin/chromium",
});
try {
  const page = await browser.newPage();
  const columns = Array.from(
    { length: 11 },
    (_, i) => `<th><button>Column ${i + 1}</button></th>`,
  ).join("");
  const cells = Array.from(
    { length: 11 },
    (_, i) => `<td>Retained version field ${i + 1}</td>`,
  ).join("");
  // The maintained Detail puts its workpaper section in .actions; preserve that
  // flex ancestry and Table's complete columns to reproduce the min-content bug.
  await page.setContent(
    `<style>${css}</style><main class="workspace"><div class="record-table"><div class="table-scroll"><table><tr>${columns}</tr><tr>${cells}</tr></table></div></div></main><dialog class="modal"><div class="modal-title"><h2>Historical workpaper</h2><button>Close</button></div><div class="actions"><section><p>Showing explicitly linked workpaper version 1. Other versions are not substituted.</p><div class="record-table"><div class="table-tools"><label class="search">Search records<input></label><span>1 records</span></div><div class="table-scroll"><table><thead><tr>${columns}</tr></thead><tbody><tr>${cells}</tr></tbody></table></div></div></section></div></dialog>`,
  );
  await page.locator("dialog").evaluate((dialog) => dialog.showModal());
  for (const width of [390, 320, 1400]) {
    await page.setViewportSize({ width, height: 844 });
    const result = await page.evaluate(() => {
      const dialog = document.querySelector("dialog");
      const section = dialog.querySelector(".actions > section");
      const scroll = dialog.querySelector(".table-scroll");
      scroll.scrollLeft = scroll.scrollWidth;
      return {
        documentWidth: document.documentElement.scrollWidth,
        viewport: innerWidth,
        modalWidth: dialog.clientWidth,
        modalScrollWidth: dialog.scrollWidth,
        sectionWidth: section.getBoundingClientRect().width,
        tableWidth: scroll.scrollWidth,
        tableViewport: scroll.clientWidth,
        scrollLeft: scroll.scrollLeft,
        columns: scroll.querySelectorAll("th").length,
        cue: getComputedStyle(dialog.querySelector(".record-table"), "::before")
          .content,
        overflow: getComputedStyle(scroll).overflowX,
      };
    });
    assert.ok(result.documentWidth <= width + 1, JSON.stringify(result));
    assert.ok(
      result.modalScrollWidth <= result.modalWidth + 1,
      JSON.stringify(result),
    );
    assert.equal(result.columns, 11);
    assert.equal(result.overflow, "auto");
    assert.ok(result.tableWidth > result.tableViewport);
    assert.ok(result.scrollLeft > 0);
    if (width <= 760)
      assert.ok(result.cue.includes("Scroll within wide tables"));
  }
  await page.locator("dialog").evaluate((dialog) => dialog.close());
  await page.setViewportSize({ width: 320, height: 844 });
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  );
  console.log(
    "PASS narrow detail: readable section, contained scrollable 11-column tables, visible cue, no document overflow",
  );
} finally {
  await browser.close();
}
