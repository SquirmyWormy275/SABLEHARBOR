import type { Engagement } from "./api";
import { useState } from "react";
import {
  inspectionArtifact,
  inspectionPins,
  recordedInspections,
} from "./artifactInspection";
export function ArtifactInspections({
  engagement: e,
  artifactId,
  onRecord,
}: {
  engagement: Engagement;
  artifactId: string;
  onRecord?: (pins: Record<string, unknown>) => void;
}) {
  const [page, setPage] = useState(0);
  const artifact = inspectionArtifact(e, artifactId);
  if (!artifact || !e.capabilities.artifact_inspections) return null;
  const rows = recordedInspections(e, artifact);
  const pages = Math.max(1, Math.ceil(rows.length / 50)),
    currentPage = Math.min(page, pages - 1);
  const writable = (e.permissions ?? []).some(
    (p) => p === "learn" || p === "instruct",
  );
  return (
    <section aria-label="Recorded evidence inspections">
      <h3>Inspection notes</h3>
      <p>
        Record the passage or section you inspected and what you observed. This
        adds an attributed audit record; it does not complete a test or
        establish understanding.
      </p>
      {writable && onRecord && (
        <button
          type="button"
          onClick={() => onRecord(inspectionPins(artifact))}
        >
          Record an inspection
        </button>
      )}
      <details>
        <summary>
          Recorded inspections of this exact original · {rows.length}
        </summary>
        {!rows.length ? (
          <p>
            No inspection record is present. The file may have been viewed
            without recording an inspection.
          </p>
        ) : (
          <ul>
            {rows.slice(currentPage * 50, (currentPage + 1) * 50).map((row) => (
              <li key={row.id}>
                <strong>{String(row.locator)}</strong>
                <p>{String(row.observation)}</p>
                <p>
                  {row.id} · Recorded by {String(row.actor)} ·{" "}
                  {String(row.recorded_at)} · revision{" "}
                  {String(row.recorded_revision)}
                  {row.task_id ? ` · Procedure ${String(row.task_id)}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
        {pages > 1 && (
          <div className="actions">
            <button
              type="button"
              disabled={currentPage === 0}
              onClick={() => setPage(currentPage - 1)}
            >
              Previous inspections
            </button>
            <span>
              Page {currentPage + 1} of {pages}
            </span>
            <button
              type="button"
              disabled={currentPage + 1 === pages}
              onClick={() => setPage(currentPage + 1)}
            >
              Next inspections
            </button>
          </div>
        )}
      </details>
    </section>
  );
}
