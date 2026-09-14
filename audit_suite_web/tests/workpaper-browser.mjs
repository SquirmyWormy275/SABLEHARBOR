// Actual local service workflow with neutral records; credentials stay private.
import { chromium } from "@playwright/test";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const base = resolve(
  "../enterprise/generated/audit-suite/build/independent-review-scratch/browser",
);
const access = JSON.parse(await readFile(base + "/access.json", "utf8"));
const browser = await chromium.launch({
  executablePath: "/usr/bin/chromium",
  headless: true,
  args: ["--no-sandbox"],
});
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
async function login(credential, view) {
  await page.goto(
    `http://127.0.0.1:8794/?engagement=${access.engagement}&view=${view}`,
  );
  await page.getByLabel("Access credential").fill(credential);
  await page.getByRole("button", { name: "Enter workroom" }).click();
  await page.locator(".workspace-footer").waitFor();
}
try {
  await login(access.preparer, "workpapers");
  // Navigation name in the approved workroom is Workpapers & review.
  await page.goto(
    `http://127.0.0.1:8794/?engagement=${access.engagement}&view=review`,
  );
  await page
    .getByRole("button", { name: access.workpaper, exact: true })
    .click();
  await page
    .getByRole("button", { name: "Save new version", exact: true })
    .click();
  await page
    .getByLabel("Work performed and explanation")
    .fill("Successor observed source, original preserved");
  await page.getByRole("button", { name: "Save record", exact: true }).click();
  await page.getByText("Saved to this engagement.", { exact: true }).waitFor();
  await page.goto(
    `http://127.0.0.1:8794/?engagement=${access.engagement}&view=notes`,
  );
  await page
    .getByRole("button", { name: "Add observation", exact: true })
    .click();
  await page.getByLabel("Control", { exact: true }).selectOption("C-NEUTRAL");
  await page
    .getByLabel("Subject", { exact: true })
    .fill("Neutral browser note");
  await page
    .getByLabel("Observation", { exact: true })
    .fill("Original neutral note");
  await page.getByRole("button", { name: "Save record", exact: true }).click();
  await page.getByText("Original neutral note", { exact: true }).waitFor();
  await page.reload();
  await page
    .getByRole("button", { name: "Correct with history", exact: true })
    .click();
  await page.getByLabel("Corrected text").fill("Corrected neutral note");
  await page
    .getByLabel("Reason for correction")
    .fill("Original wording clarified");
  await page.getByRole("button", { name: "Save record", exact: true }).click();
  await page.getByText("Corrected neutral note", { exact: true }).waitFor();
  await page.context().clearCookies();
  await login(access.reviewer, "review");
  await page
    .getByRole("button", { name: access.workpaper, exact: true })
    .click();
  await page
    .getByRole("button", { name: "Review version 1", exact: true })
    .click();
  await page
    .getByLabel("Independent review comment")
    .fill("Version one remains limited; review pinned");
  await page.getByRole("button", { name: "Save record", exact: true }).click();
  await page
    .getByText("Version one remains limited; review pinned", { exact: true })
    .waitFor();
  const state = await page.evaluate(
    async (id) => (await fetch("/api/engagements/" + id)).json(),
    access.engagement,
  );
  if (
    state.workpapers[0].versions.length !== 2 ||
    state.reviews[0].workpaper_version !== 1 ||
    state.notes[0].history[0].text !== "Original neutral note"
  )
    throw Error("Native version/history mismatch");
  if (errors.length) throw Error(errors.join("\n"));
  await page.screenshot({ path: base + "/review-version.png", fullPage: true });
  await writeFile(
    base + "/receipt.json",
    JSON.stringify(
      {
        status: "PASS_ACTUAL_BROWSER_SERVICE",
        workpaper_versions: 2,
        reviewed_version: 1,
        note_original_preserved: true,
        checks: [
          "Actual browser successor workpaper command",
          "Actual browser note create/correct and original history",
          "Actual independent reviewer comment pinned to v1 and rendered",
        ],
        limits:
          "Neutral source/control fixture; actual browser commands and durable service history",
        errors,
      },
      null,
      2,
    ),
    { mode: 0o600 },
  );
} finally {
  await browser.close();
}
