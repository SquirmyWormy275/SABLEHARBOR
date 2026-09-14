import { useState } from "react";
import type { Engagement, Row } from "./api";
import { str } from "./api";
import { ActionForm, Table, type Action, type Field } from "./components";
const field = (
  name: string,
  label: string,
  type: Field["type"] = "text",
): Field => ({ name, label, type, required: true });
const choice = (
  name: string,
  label: string,
  options: { value: string; label: string }[],
): Field => ({ name, label, type: "select", options, required: true });
const values = (items: string[]) =>
  items.map((value) => ({ value, label: value }));
export default function TemporalCoverage({
  engagement: e,
  busy,
  onCommand,
}: {
  engagement: Engagement;
  busy: boolean;
  onCommand: (
    kind: string,
    p: Record<string, unknown>,
  ) => Promise<Engagement | undefined>;
}) {
  const [action, setAction] = useState<Action | null>(null);
  const current = (e.temporal_current ?? {}) as Record<string, Row[]>;
  const versions = current.versions ?? [],
    reports = (e.temporal_reports ?? []) as Row[],
    work = current.work ?? [],
    proposals = current.proposals ?? [];
  const implementation = choice(
    "implementation_id",
    "Dated implementation",
    versions.map((v) => ({
      value: v.id,
      label: `${str(v.control_id)} · ${str(v.boundary_id)} · ${str(v.effective)}`,
    })),
  );
  return (
    <details className="panel">
      <summary>
        Dated work, remaining-period coverage and implementation changes
      </summary>
      <p>
        Engagement timezone: {str(e.scope.timezone ?? "UTC")}. Date-only
        procedure and coverage entries use this timezone.
      </p>
      <p>
        Audit period, procedure dates and evidence receipt are separate. Gaps
        and exceptions remain visible; recorded coverage is not a professional
        sufficiency conclusion. Changes preserve earlier work and may require
        reassessment.
      </p>
      <div className="actions">
        <button
          disabled={busy || !versions.length}
          onClick={() =>
            setAction({
              title: "Record dated procedure coverage",
              kind: "coverage.record",
              fields: [
                implementation,
                field("covered_start", "Covered period start", "date"),
                field("covered_end", "Covered period end (inclusive)", "date"),
                field("performed_at", "Procedure performed on", "date"),
                choice(
                  "procedure_kind",
                  "Procedure kind",
                  values([
                    "TOD",
                    "IMPLEMENTATION",
                    "TOE",
                    "SUBSTANTIVE",
                    "ROLL_FORWARD",
                    "INQUIRY",
                  ]),
                ),
                choice(
                  "result",
                  "Recorded disposition",
                  values([
                    "RECORDED",
                    "EXCEPTION",
                    "INSUFFICIENT_EVIDENCE",
                    "NO_CHANGE_REPORTED",
                    "NOT_CONCLUDED",
                  ]),
                ),
                {
                  ...field(
                    "evidence_ids",
                    "Retained evidence IDs, separated by commas",
                  ),
                  required: false,
                },
                field("rationale", "Rationale and limits", "textarea"),
                field("methodology", "Methodology", "textarea"),
                field(
                  "nature_timing_extent",
                  "Nature, timing and extent",
                  "textarea",
                ),
              ],
            })
          }
        >
          Record dated work
        </button>
        <button
          disabled={busy || !versions.length}
          onClick={() =>
            setAction({
              title: "Record an implementation change",
              kind: "implementation.change",
              fields: [
                implementation,
                field("effective_at", "Effective change date", "date"),
                choice(
                  "owner_id",
                  "Owner after change",
                  e.people.map((p) => ({ value: p.id, label: str(p.name) })),
                ),
                field("implementation_version", "New implementation version"),
                field(
                  "rationale",
                  "Source-supported reason for change",
                  "textarea",
                ),
              ],
            })
          }
        >
          Record implementation change
        </button>
        <button
          disabled={busy || !e.requests.length}
          onClick={() =>
            setAction({
              title: "Propose remaining-period work",
              kind: "coverage.propose_remaining",
              description:
                "This saves a proposal and manual task. Confirm separately to issue or follow up on the selected existing source requests.",
              fields: [
                choice(
                  "control_id",
                  "Scoped control",
                  e.controls.map((c) => ({
                    value: c.id,
                    label: c.id + " · " + str(c.title),
                  })),
                ),
                choice(
                  "boundary_id",
                  "Scoped boundary",
                  values(e.scope.boundaries),
                ),
                field(
                  "source_request_ids",
                  "Current source PBC IDs, separated by commas",
                ),
                field("message", "Proposed company request", "textarea"),
                field("rationale", "Remaining-work rationale", "textarea"),
              ],
            })
          }
        >
          Propose remaining work
        </button>
      </div>
      <h3>Current coverage and unresolved periods</h3>
      <Table
        rows={reports.map((r, i) => ({ ...r, id: String(i) }))}
        columns={[
          { key: "control_id", label: "Control" },
          { key: "boundary_id", label: "Boundary" },
          {
            key: "versions",
            label: "Unaddressed periods",
            render: (r) =>
              str(
                ((r.versions as Row[]) ?? []).map((v) => ({
                  implementation: v.implementation_id,
                  gaps: v.gaps,
                  limitations: v.limitation_ids,
                })),
              ),
          },
          { key: "historical_exception_ids", label: "Exceptions" },
          {
            key: "records_requiring_reassessment",
            label: "Work requiring reassessment",
          },
          {
            key: "reported_work_complete",
            label: "Recorded work spans scope",
            render: (r) =>
              r.reported_work_complete
                ? "Recorded coverage only"
                : "Unaddressed work remains",
          },
        ]}
      />
      <h3>Retained procedure records</h3>
      <Table
        rows={work}
        columns={[
          { key: "implementation_id", label: "Implementation" },
          { key: "covered", label: "Coverage" },
          { key: "performed_at", label: "Performed" },
          { key: "received_at", label: "Evidence received" },
          { key: "kind", label: "Procedure" },
          { key: "result", label: "Disposition" },
          { key: "evidence_ids", label: "Original references" },
        ]}
      />
      <h3>Remaining-work proposals</h3>
      <Table
        rows={proposals}
        columns={[
          { key: "control_id", label: "Control" },
          { key: "message", label: "Proposed request" },
          { key: "status", label: "Status" },
          {
            key: "id",
            label: "Confirm exchange",
            render: (r) => (
              <button
                disabled={busy || r.status !== "PROPOSED"}
                onClick={() =>
                  setAction({
                    title: "Confirm remaining-work exchange",
                    kind: "coverage.confirm_remaining",
                    initial: { id: r.id, message: r.message },
                    description:
                      "Confirmation issues or follows up on the linked PBC requests. It does not erase prior evidence or reset scenario clocks.",
                    fields: [
                      field("message", "Confirmed company request", "textarea"),
                    ],
                  })
                }
              >
                Confirm request
              </button>
            ),
          },
        ]}
      />
      {action && (
        <ActionForm
          action={action}
          busy={busy}
          onClose={() => setAction(null)}
          onSubmit={async (p) => {
            for (const key of ["evidence_ids", "source_request_ids"])
              if (typeof p[key] === "string")
                p[key] = (p[key] as string)
                  .split(/[\n,]+/)
                  .map((s) => s.trim())
                  .filter(Boolean);
            const result = await onCommand(action.kind, p);
            if (result) setAction(null);
          }}
        />
      )}
    </details>
  );
}
