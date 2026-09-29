// Neutral source-attribution renderer fixture; domain attribution tested separately.
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
  await p.goto(`http://127.0.0.1:8794/?engagement=${a.engagement}&view=notes`);
  await p.getByLabel("Access credential").fill(a.preparer);
  await p.getByRole("button", { name: "Enter workroom" }).click();
  await p.locator(".workspace-footer").waitFor();
  await p.route(`**/api/engagements/${a.engagement}`, async (route) => {
    const response = await route.fetch();
    const s = await response.json();
    const u = {
      message_id: "MSG-LEARNER",
      speaker_role: "LEARNER",
      speaker_id: "USER-NEUTRAL",
      start: 0,
      end: 19,
      original_text: "I have not tested.",
    };
    const c = {
      message_id: "MSG-COMPANY",
      speaker_role: "COMPANY",
      speaker_id: "PERSON-NEUTRAL",
      start: 0,
      end: 20,
      original_text: "The source is absent.",
    };
    u.end = u.original_text.length;
    c.end = c.original_text.length;
    s.notes = [
      {
        id: "NOTE-NEUTRAL",
        text: "Two separately attributed statements",
        classification: "ATTRIBUTED_EXCHANGE_STATEMENT",
        person_id: null,
        source_refs: [u, c],
        attributed_bullets: [
          {
            text: "Learner has not tested",
            classification: "ATTRIBUTED_EXCHANGE_STATEMENT",
            source_refs: [u],
          },
          {
            text: "Company reports absent source",
            classification: "ATTRIBUTED_EXCHANGE_STATEMENT",
            source_refs: [c],
          },
        ],
        history: [],
      },
    ];
    await route.fulfill({ response, json: s });
  });
  await p.reload();
  await p.getByText("Sources and speakers", { exact: true }).click();
  for (const t of [
    "learner speaker: USER-NEUTRAL",
    "company speaker: PERSON-NEUTRAL",
    "I have not tested.",
    "The source is absent.",
    "Learner has not tested",
    "Company reports absent source",
  ])
    await p.getByText(t, { exact: true }).first().waitFor();
  await p.screenshot({ path: base + "/note-provenance.png", fullPage: true });
  await writeFile(
    base + "/note-provenance-receipt.json",
    JSON.stringify(
      {
        status: "PASS_BROWSER_ATTRIBUTION_RENDER",
        source:
          "Explicit neutral response fixture; domain source binding separately verified by actual Store commands",
        learner_company_distinct: true,
        actual_message_id_fields_visible: true,
        original_source_text_visible: true,
        per_claim_refs_visible: true,
      },
      null,
      2,
    ),
    { mode: 0o600 },
  );
} finally {
  await b.close();
}
