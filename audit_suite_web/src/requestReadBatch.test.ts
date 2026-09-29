import { describe, it, expect } from "vitest";
import type { Engagement } from "./api";
import {
  planRequestReads,
  acceptedReadResponse,
  requestReadAuthority,
} from "./requestReadBatch";
const e = {
  id: "E",
  revision: 1,
  phase: "ACTIVE",
  scope: { boundaries: ["corporate"] },
  permissions: ["learn"],
  requests: [
    { id: "R1", title: "Received original", unread: true },
    { id: "R2", title: "Already read", unread: false },
    { id: "R3", title: "Other boundary", unread: true, boundary_id: "other" },
  ],
} as unknown as Engagement;
describe("administrative request-read snapshot", () => {
  it("counts exact selected/filtered/eligible/excluded IDs without inferring acceptance", () => {
    const p = planRequestReads(
      e,
      "",
      ["R1", "R2", "R3", "missing"],
      "SELECTED",
    );
    expect(p.eligible).toEqual(["R1"]);
    expect(p.selected).toBe(4);
    expect(p.matched).toBe(3);
    expect(p.excluded).toHaveLength(3);
    expect(planRequestReads(e, "Already", ["R1"], "SELECTED").excluded).toEqual(
      [{ id: "R1", reason: "Outside current filter" }],
    );
  });
  it("never truncates a filtered set to the twenty limit", () => {
    const many = {
      ...e,
      requests: Array.from({ length: 21 }, (_, i) => ({
        id: `R${i}`,
        unread: true,
      })),
    };
    const p = planRequestReads(many, "", [], "FILTERED");
    expect(p.overLimit).toBe(true);
    expect(p.eligible).toHaveLength(21);
  });
  it("rejects ambiguous identity and requires actual boolean unread", () => {
    expect(
      planRequestReads(
        { ...e, requests: [...e.requests, e.requests[0]] },
        "",
        ["R1"],
        "SELECTED",
      ).eligible,
    ).toEqual([]);
    expect(
      planRequestReads(
        { ...e, requests: [{ id: "R1", unread: "true" }] },
        "",
        ["R1"],
        "SELECTED",
      ).eligible,
    ).toEqual([]);
  });
  it("accepts only exact next revision, engagement and target unread false", () => {
    const c = {
        command_id: "C",
        expected_revision: 1,
        kind: "pbc.read" as const,
        payload: { request_id: "R1" },
      },
      reply = { ...e, revision: 2, requests: [{ id: "R1", unread: false }] };
    expect(acceptedReadResponse(e, c, reply)).toBe(true);
    expect(acceptedReadResponse(e, c, { ...reply, revision: 3 })).toBe(false);
    expect(acceptedReadResponse(e, c, { ...reply, id: "OTHER" })).toBe(false);
    expect(
      acceptedReadResponse(e, c, {
        ...reply,
        requests: [{ id: "R2", unread: false }],
      }),
    ).toBe(false);
    expect(requestReadAuthority(e, "P")).not.toBe(
      requestReadAuthority({ ...e, permissions: ["review"] }, "P"),
    );
  });
});
