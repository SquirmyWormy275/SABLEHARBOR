import { expect, it } from "vitest";
import type { Engagement } from "./api";
import { recordedFeedback, reviewFeedbackTarget } from "./reviewFeedback";
const fixture = () =>
  ({
    id: "E",
    permissions: ["learn"],
    reviews: [
      { id: "H", kind: "HUMAN", status: "OPEN", workpaper_id: "W" },
      {
        id: "A",
        kind: "EXPERIMENTAL_AI",
        status: "SUGGESTIONS_ONLY",
        input_digest: "a".repeat(64),
      },
      { id: "P", kind: "EXPERIMENTAL_INPUT", status: "PREPARED" },
    ],
    workpapers: [{ id: "W", versions: [{ version: 1 }, { version: 2 }] }],
  }) as unknown as Engagement;
it("learner human feedback pins current version and leaves source status untouched", () => {
  const e = fixture();
  expect(reviewFeedbackTarget(e, "H", true).payload).toEqual({
    review_id: "H",
    response_workpaper_version: 2,
  });
  expect(e.reviews[0].status).toBe("OPEN");
  e.workpapers[0].versions = [{ version: 1 }, { version: 3 }];
  expect(
    reviewFeedbackTarget(e, "H", true).payload?.response_workpaper_version,
  ).toBe(3);
});
it("experimental appeal pins original input without inferring a workpaper", () => {
  const e = fixture();
  expect(reviewFeedbackTarget(e, "A", true).payload).toEqual({
    review_id: "A",
    input_digest: "a".repeat(64),
  });
  expect(e.reviews[1].status).toBe("SUGGESTIONS_ONLY");
});
it("denies prepared, stale, unsupported server and revoked role forms", () => {
  const e = fixture();
  for (const id of ["P", "missing"])
    expect(reviewFeedbackTarget(e, id, true).payload).toBeNull();
  expect(reviewFeedbackTarget(e, "H", false).payload).toBeNull();
  e.permissions = [];
  expect(reviewFeedbackTarget(e, "H", true).payload).toBeNull();
});
it("keeps AI appeals distinct from human and legacy history", () => {
  const e = fixture();
  e.reviews[0].history = [
    { response: "Earlier resolution", status: "OPEN" },
    { response: "Disagree", disposition: "disagree" },
  ];
  e.reviews[1].appeals = [
    {
      response: "Request review",
      disposition: "human_review",
      input_digest: "a",
    },
  ];
  e.reviews[1].history = [{ response: "Wrong channel" }];
  expect(recordedFeedback(e.reviews[0])).toHaveLength(2);
  expect(recordedFeedback(e.reviews[1]).map((x) => x.response)).toEqual([
    "Request review",
  ]);
});
