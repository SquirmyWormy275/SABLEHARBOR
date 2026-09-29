// Neutral renderer fixture, no model or backend grading claim.
import { chromium } from "@playwright/test";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const base = resolve(
  "../enterprise/generated/audit-suite/build/independent-review-scratch/browser",
);
const a = JSON.parse(await readFile(base + "/access.json", "utf8"));
const b = await chromium.launch({
  executablePath: "/usr/bin/chromium",
  headless: true,
  args: ["--no-sandbox"],
});
try {
  const p = await b.newPage();
  await p.goto(`http://127.0.0.1:8794/?engagement=${a.engagement}&view=review`);
  await p.getByLabel("Access credential").fill(a.reviewer);
  await p.getByRole("button", { name: "Enter workroom" }).click();
  await p.locator(".workspace-footer").waitFor();
  await p.route(`**/api/engagements/${a.engagement}`, async (r) => {
    const response = await r.fetch();
    const s = await response.json();
    s.reviews.push({
      id: "AI-NEUTRAL-RENDER",
      kind: "EXPERIMENTAL_AI",
      warning: "Experimental neutral renderer fixture",
      status: "SUGGESTIONS_ONLY",
      result: {
        text: "Bounded observation",
        findings: [
          {
            category: "REQUIRES_REVIEW",
            claim: "Neutral unresolved source",
            learner_excerpt: {
              source_ref: "WP-NEUTRAL:v1",
              text: "Neutral quoted observation",
            },
            source_refs: ["WP-NEUTRAL:v1"],
            rationale: "Inspect the retained source",
            uncertainty: "Scope is limited",
            suggested_followup: "Obtain corroboration",
          },
        ],
        observations: [
          {
            text: "Historical observation remains readable",
            source_refs: [],
            limitation: "Historical fixture",
          },
        ],
      },
    });
    await r.fulfill({ response, json: s });
  });
  await p.reload();
  await p
    .getByRole("button", { name: "AI-NEUTRAL-RENDER", exact: true })
    .click();
  for (const t of [
    "Neutral unresolved source",
    "Neutral quoted observation",
    "Inspect the retained source",
    "Uncertainty: Scope is limited",
    "Suggested follow-up: Obtain corroboration",
    "Historical observation remains readable",
  ])
    await p
      .getByText(t, { exact: t !== "Historical observation remains readable" })
      .waitFor();
  await p.screenshot({ path: base + "/typed-findings.png", fullPage: true });
  await writeFile(
    base + "/typed-findings-receipt.json",
    JSON.stringify(
      {
        status: "PASS_BROWSER_TYPED_RENDER",
        source:
          "Explicit neutral response fixture; no model or backend grading claim",
        object_excerpt: true,
        legacy_observations: true,
        fields: [
          "category",
          "claim",
          "learner_excerpt.text",
          "learner_excerpt.source_ref",
          "source_refs",
          "rationale",
          "uncertainty",
          "suggested_followup",
        ],
      },
      null,
      2,
    ),
    { mode: 0o600 },
  );
} finally {
  await b.close();
}
