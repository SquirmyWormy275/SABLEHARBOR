import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Engagement } from "./api";
import { ProcedureTraceReadiness } from "./ProcedureTraceReadiness";
import type { TraceReadiness } from "./traceReadiness";
import {
  currentIntegrity,
  traceIntegrity,
  type OriginalIntegrity,
} from "./procedureIntegrity";

const engagement = { id: "ENG-1", revision: 4 } as Engagement;
const report: OriginalIntegrity = {
  schema_version: "1.0",
  engagement_id: "ENG-1",
  engagement_revision: 4,
  status: "VERIFIED_RETAINED_BYTES_ONLY",
  metadata_status: "AVAILABLE",
  automatic_testing_credit: false,
  counts: {
    referenced: 1,
    verified: 1,
    missing: 0,
    integrity_failure: 0,
    read_unavailable: 0,
  },
  artifacts: [{ artifact_id: "ART-1", status: "VERIFIED_RETAINED_BYTES" }],
  traces: [
    {
      id: "TRACE-1",
      status: "VERIFIED_RETAINED_BYTES",
      artifact_ids: ["ART-1"],
    },
  ],
};

describe("retained original UI boundaries", () => {
  it("rejects a stale engagement revision and any credit claim", () => {
    expect(currentIntegrity(report, engagement)).toBe(true);
    expect(
      currentIntegrity({ ...report, engagement_revision: 3 }, engagement),
    ).toBe(false);
    expect(
      currentIntegrity(
        {
          ...report,
          automatic_testing_credit: true,
        } as unknown as OriginalIntegrity,
        engagement,
      ),
    ).toBe(false);
  });

  it("rejects malformed or contradictory byte-check results", () => {
    expect(
      currentIntegrity(
        { ...report, metadata_status: "INPUT_UNAVAILABLE", counts: null },
        engagement,
      ),
    ).toBe(false);
    expect(
      currentIntegrity(
        { ...report, counts: { ...report.counts!, referenced: 2 } },
        engagement,
      ),
    ).toBe(false);
    expect(currentIntegrity({ ...report, status: "UNKNOWN" }, engagement)).toBe(
      false,
    );
    expect(
      currentIntegrity(
        {
          ...report,
          traces: [{ id: "TRACE-1", status: "METADATA_UNAVAILABLE" }],
        },
        engagement,
      ),
    ).toBe(false);
  });

  it("does not attach an ambiguous trace result to a procedure", () => {
    expect(traceIntegrity(report, "TRACE-1")?.status).toBe(
      "VERIFIED_RETAINED_BYTES",
    );
    expect(
      traceIntegrity(
        { ...report, traces: [...report.traces, report.traces[0]] },
        "TRACE-1",
      ),
    ).toBeNull();
  });

  it("shows the separate byte result beside a recorded trace without implying audit credit", () => {
    const data = {
      status: "RECORDED_TRACE_LINKS",
      trace_count: 1,
      current_leaf_count: 1,
      current_leaf_item_status_counts: { OBSERVED: 1 },
      lineages: [
        {
          root_id: "TRACE-1",
          current_leaf_id: "TRACE-1",
          status: "EXACT_VISIBLE_METADATA_LINKS",
          historical_trace_ids: [],
        },
      ],
      traces: [
        {
          id: "TRACE-1",
          status: "EXACT_VISIBLE_METADATA_LINKS",
          reason_codes: [],
          exact_refs: [],
          selected_item_count: 1,
          items_with_no_recorded_observation_count: 0,
        },
      ],
    } as TraceReadiness;
    const html = renderToStaticMarkup(
      createElement(ProcedureTraceReadiness, {
        engagement,
        data,
        integrity: report,
        onPreview: () => {},
      }),
    );
    expect(html).toContain("Retained-copy check:");
    expect(html).toContain("Retained bytes match the recorded size and hash.");
    expect(html).toContain("do not establish completeness");
  });
});
