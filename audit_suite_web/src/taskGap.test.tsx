import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import type { Engagement } from "./api";
import { TaskGapPanel, TaskGapPreview } from "./TaskGapPanel";
import {
  acceptedTaskGap,
  canRecordTaskGap,
  currentTaskGaps,
  taskGapCommand,
  taskGapRows,
  taskEligibleForGap,
  type TaskGapDraft,
} from "./taskGap";

const sha = "a".repeat(64);
const state = {
  id: "E",
  revision: 7,
  phase: "ACTIVE",
  permissions: ["learn"],
  tasks: [
    {
      id: "T",
      title: "Inspect source collection",
      status: "NOT_STARTED",
      conclusion: "NOT_RUN",
    },
  ],
  artifacts: [
    {
      id: "A",
      status: "AVAILABLE",
      sha256: sha,
      title: "Native source receipt",
    },
  ],
  workpapers: [
    {
      id: "W",
      versions: [{ version: 2, task_ids: ["T"], conclusion: "LIMITATION" }],
    },
  ],
  task_gaps: [],
} as unknown as Engagement;
const draft: TaskGapDraft = {
  cause: "INSUFFICIENT_SOURCE",
  owner_id: "L",
  disposition: "RETEST_LINKED",
  narrative:
    "The collected native source does not support this procedure's exact clock assertion.",
  artifact_id: "A",
  retest_key: "W:v2",
  predecessor_id: "",
};

it("previews exact source and retest references without changing task conclusion", () => {
  const cmd = taskGapCommand(state, "L", "T", draft, "COMMAND-1");
  expect(Object.keys(cmd.payload).sort()).toEqual([
    "artifact_pin",
    "cause",
    "disposition",
    "narrative",
    "owner_id",
    "predecessor_id",
    "retest",
    "task_id",
  ]);
  expect(cmd.payload.artifact_pin).toEqual({ id: "A", sha256: sha });
  expect(cmd.payload.retest).toEqual({ workpaper_id: "W", version: 2 });
  const html = renderToStaticMarkup(<TaskGapPreview command={cmd} />);
  expect(html).toContain(sha);
  expect(html).toContain("W version 2");
  expect(html).toContain("No status, conclusion, or retest result is inferred");
  expect(state.tasks[0].conclusion).toBe("NOT_RUN");
});

it("holds an exact command for retry and rejects a revision-only success", () => {
  const cmd = taskGapCommand(state, "L", "T", draft, "COMMAND-1");
  const edited = { ...draft, narrative: "Changed after preview" };
  expect(cmd.payload.narrative).not.toBe(edited.narrative);
  const row = {
    id: "GAP-1",
    ...cmd.payload,
    actor: "L",
    revision: 8,
    recorded_at: "2027-02-01T00:00:00Z",
    qualification: "AUTHOR_RECORDED_GAP_NOT_EVIDENCE_OR_AUDIT_CONCLUSION",
  };
  const after = { ...state, revision: 8, task_gaps: [row] } as Engagement;
  expect(acceptedTaskGap(state, after, "L", cmd)).toBe(true);
  expect(acceptedTaskGap(state, { ...after, task_gaps: [] }, "L", cmd)).toBe(
    false,
  );
  expect(
    acceptedTaskGap(
      state,
      { ...after, task_gaps: [{ ...row, actor: "OTHER" }] },
      "L",
      cmd,
    ),
  ).toBe(false);
  expect(
    acceptedTaskGap(
      state,
      { ...after, task_gaps: [{ ...row, narrative: "Other" }] },
      "L",
      cmd,
    ),
  ).toBe(false);
  expect(cmd.command_id).toBe("COMMAND-1");
});

it("restricts recording by role and phase while showing read-only history", () => {
  const review = {
    ...state,
    permissions: ["review"],
    task_gaps: [
      {
        id: "GAP-1",
        task_id: "T",
        cause: "DENIED_ACCESS",
        owner_id: "L",
        disposition: "OPEN",
        narrative:
          "Access denied to this exact source despite a documented request.",
        artifact_pin: null,
        retest: null,
        predecessor_id: null,
        actor: "L",
        revision: 7,
        recorded_at: "2027-02-01T00:00:00Z",
      },
    ],
  } as Engagement;
  expect(canRecordTaskGap(review)).toBe(false);
  expect(() => taskGapCommand(review, "L", "T", draft, "NEW")).toThrow();
  expect(canRecordTaskGap({ ...state, phase: "READY" })).toBe(false);
  const html = renderToStaticMarkup(
    <TaskGapPanel
      engagement={review}
      taskId="T"
      viewerId="R"
      onState={() => {}}
      onClose={() => {}}
    />,
  );
  expect(html).toContain("Access denied to this exact source");
  expect(html).not.toContain("Preview exact record");
  expect(html).toContain("History remains read-only");
});

it("keeps excluded and not-applicable task history readable without permitting a new gap", () => {
  for (const patch of [
    { status: "NOT_APPLICABLE" },
    { status: "EXCLUDED" },
    { applicable: false },
  ]) {
    const task = { ...state.tasks[0], ...patch };
    const scoped = { ...state, tasks: [task] } as Engagement;
    expect(taskEligibleForGap(task)).toBe(false);
    expect(() => taskGapCommand(scoped, "L", "T", draft, "C")).toThrow();
    const html = renderToStaticMarkup(
      <TaskGapPanel engagement={scoped} taskId="T" viewerId="L" onState={() => {}} onClose={() => {}} />,
    );
    expect(html).toContain("History remains read-only");
    expect(html).not.toContain("Preview exact record");
  }
});

it("requires exact current artifact, task-linked retest and same-task predecessor", () => {
  const prior = {
    id: "GAP-OLD",
    task_id: "T",
    cause: "MISSING_OPERATION",
    owner_id: "L",
    disposition: "OPEN",
    narrative: "Prior missing operation observed for the same exact task.",
    artifact_pin: null,
    retest: null,
    predecessor_id: null,
    actor: "L",
    revision: 6,
    recorded_at: "2027-01-01T00:00:00Z",
  };
  const withPrior = { ...state, task_gaps: [prior] } as Engagement;
  expect(
    taskGapCommand(
      withPrior,
      "L",
      "T",
      { ...draft, predecessor_id: "GAP-OLD" },
      "C",
    ).payload.predecessor_id,
  ).toBe("GAP-OLD");
  expect(() =>
    taskGapCommand(
      withPrior,
      "L",
      "T",
      { ...draft, predecessor_id: "OTHER" },
      "C",
    ),
  ).toThrow();
  expect(() =>
    taskGapCommand(
      { ...state, artifacts: [{ id: "A", status: "MISSING", sha256: sha }] },
      "L",
      "T",
      draft,
      "C",
    ),
  ).toThrow();
  expect(() =>
    taskGapCommand(state, "L", "T", { ...draft, retest_key: "W:v9" }, "C"),
  ).toThrow();
  const followed = {
    ...prior,
    id: "GAP-NEXT",
    predecessor_id: prior.id,
    revision: 7,
  };
  const rows = taskGapRows(
    { ...state, task_gaps: [prior, followed] } as Engagement,
    "T",
  );
  expect(currentTaskGaps(rows).map((r) => r.id)).toEqual(["GAP-NEXT"]);
});
