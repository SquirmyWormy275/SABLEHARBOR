import { describe, it, expect } from "vitest";
import type { Engagement } from "./api";
import {
  handoffAuthority,
  freezeHandoffCommand,
  resolveHandoffReference,
} from "./investigationHandoffs";
const e = {
  id: "E",
  revision: 4,
  scope: {},
  permissions: ["learn"],
  workpapers: [{ id: "W", versions: [{ version: 1 }, { version: 2 }] }],
  artifacts: [{ id: "A", version: 1, status: "AVAILABLE" }],
} as unknown as Engagement;
const pin = {
  kind: "workpaper" as const,
  id: "W",
  version: 1,
  sha256: "a".repeat(64),
};
describe("explicit investigation handoff boundaries", () => {
  it("keeps ordinary revision changes separate from authority changes", () => {
    expect(handoffAuthority({ ...e, revision: 5 }, "P")).toBe(
      handoffAuthority(e, "P"),
    );
    expect(handoffAuthority({ ...e, permissions: ["review"] }, "P")).not.toBe(
      handoffAuthority(e, "P"),
    );
    expect(handoffAuthority(e, "Q")).not.toBe(handoffAuthority(e, "P"));
  });
  it("selects only an exact retained workpaper version", () => {
    expect(
      resolveHandoffReference(e, pin, "HISTORICAL_VERSION_AVAILABLE")?.id,
    ).toBe("W");
    expect(
      resolveHandoffReference(e, { ...pin, version: 3 }, "EXACT_PIN_AVAILABLE"),
    ).toBeNull();
    expect(resolveHandoffReference(e, pin, "CONTENT_CHANGED")).toBeNull();
    expect(
      resolveHandoffReference(
        { ...e, workpapers: [...e.workpapers, ...e.workpapers] },
        pin,
        "EXACT_PIN_AVAILABLE",
      ),
    ).toBeNull();
  });
  it("detaches the exact command body before later form edits", () => {
    const body = {
      command_id: "one",
      payload: { question: "Original question", links: [pin] },
    };
    const pending = freezeHandoffCommand("/handoffs", body);
    body.payload.question = "Later text";
    body.payload.links[0] = { ...pin, version: 2 };
    expect(pending.body).toEqual({
      command_id: "one",
      payload: { question: "Original question", links: [pin] },
    });
  });
});

import {
  currentHandoff,
  handoffWaiting,
  type Handoff,
} from "./investigationHandoffs";
const handoff = {
  id: "H",
  version: 1,
  status: "OFFERED",
  engagement_id: "E",
  current_engagement_revision: 4,
  sender_id: "P",
  recipient_id: "Q",
  acting_role: "SENDER",
  shared_content_visible: true,
  context_status: "CURRENT",
  allowed_actions: ["WITHDRAW"],
} as Handoff;
it("rejects another participant or stale response revision", () => {
  expect(currentHandoff(handoff, e, "P")).toBe(true);
  expect(currentHandoff(handoff, e, "stranger")).toBe(false);
  expect(
    currentHandoff({ ...handoff, current_engagement_revision: 3 }, e, "P"),
  ).toBe(false);
});
it("labels recipient responsibility and coordination completion", () => {
  expect(handoffWaiting(handoff, "Q")).toBe("Awaiting your decision");
  expect(handoffWaiting({ ...handoff, status: "ACCEPTED" }, "P")).toBe(
    "Awaiting Q's response",
  );
  expect(handoffWaiting({ ...handoff, status: "COMPLETED" }, "Q")).toBe(
    "Coordination response completed",
  );
});
it("rejects a retained artifact whose exact SHA changed", () => {
  const ref = {
    kind: "artifact" as const,
    id: "A",
    version: 1,
    sha256: "a".repeat(64),
  };
  expect(
    resolveHandoffReference(
      {
        ...e,
        artifacts: [
          { id: "A", version: 1, status: "AVAILABLE", sha256: "b".repeat(64) },
        ],
      },
      ref,
      "EXACT_PIN_AVAILABLE",
    ),
  ).toBeNull();
});
