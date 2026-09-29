import { useRef, useState } from "react";
import type { Engagement } from "./api";
import type { EvidenceContextReference } from "./evidenceContext";
import {
  sampleOriginalContext,
  sampleObservationReference,
  type SampleObservation,
} from "./sampleOriginalObservations";
import "./sampleEvidenceContext.css";
export function SampleEvidenceContext({
  engagement: e,
  artifactId,
  onOpen,
}: {
  engagement: Engagement;
  artifactId: string;
  onOpen: (r: EvidenceContextReference) => void;
}) {
  const [search, setSearch] = useState(""),
    [page, setPage] = useState(0),
    current = useRef(e);
  current.current = e;
  const context = sampleOriginalContext(e, artifactId),
    matches = context.rows.filter((r) =>
      [
        r.traceId,
        r.itemId,
        r.status,
        r.observation,
        ...r.locators,
        r.taskId,
        r.workpaperId,
      ]
        .join(" ")
        .toLowerCase()
        .includes(search.toLowerCase()),
    );
  const navigate = (row: SampleObservation, kind: "task" | "workpaper") => {
    const reference = sampleObservationReference(current.current, row, kind);
    if (reference) onOpen(reference);
  };
  return (
    <section
      className="sample-evidence-context"
      aria-label="Recorded sample item observations"
    >
      <h4>Item observations citing this exact original</h4>
      <p>
        These are author-recorded observations and locators, not automatic
        passing results or independent review. Earlier revisions remain visible
        after correction.
      </p>
      {context.unavailable && (
        <p role="status">
          Some sample context is unavailable or exceeds the bounded index; no
          complete-history claim is made.
        </p>
      )}
      {!context.rows.length && !context.unavailable && (
        <p>
          No recorded sample item cites this artifact ID and SHA-256. This does
          not establish whether testing was performed elsewhere.
        </p>
      )}
      {context.rows.length > 0 && (
        <>
          <label>
            Find observations for this original
            <input
              type="search"
              value={search}
              onChange={(x) => {
                setSearch(x.target.value);
                setPage(0);
              }}
            />
          </label>
          <p>
            {matches.length} matching observations of {context.rows.length}{" "}
            exact-original citations · page {page + 1}
          </p>
          <div>
            <button disabled={page === 0} onClick={() => setPage(page - 1)}>
              Previous observations
            </button>
            <button
              disabled={(page + 1) * 10 >= matches.length}
              onClick={() => setPage(page + 1)}
            >
              Next observations
            </button>
          </div>
          {matches.slice(page * 10, page * 10 + 10).map((r) => (
            <article key={r.traceId + ":" + r.revision + ":" + r.itemId}>
              <h5>
                Item {r.itemId} · {r.status.toLowerCase().replaceAll("_", " ")}
              </h5>
              <p className="sample-observation-text">{r.observation}</p>
              <p>
                Locator{r.locators.length === 1 ? "" : "s"}:{" "}
                {r.locators.join(" · ")}
              </p>
              <p>
                Trace {r.traceId} · revision {r.revision}
                {r.predecessorId ? ` · Corrects ${r.predecessorId}` : ""}
              </p>
              {r.successors.map((s) => (
                <p key={s.id}>
                  Correction recorded: {s.id} · revision {s.revision}
                  {s.citesOriginal
                    ? " · also cites this exact original"
                    : " · does not cite this exact original"}
                  . This earlier observation is preserved.
                </p>
              ))}
              <div>
                {sampleObservationReference(e, r, "task") ? (
                  <button onClick={() => navigate(r, "task")}>
                    Open procedure:{" "}
                    {String(
                      e.tasks.find((t) => t.id === r.taskId)?.title ??
                        e.tasks.find((t) => t.id === r.taskId)?.procedure ??
                        "Untitled procedure",
                    )}
                  </button>
                ) : (
                  <p>
                    Procedure {r.taskId}: exact recorded pin is unavailable in
                    the current input index.
                  </p>
                )}
                {sampleObservationReference(e, r, "workpaper") ? (
                  <button onClick={() => navigate(r, "workpaper")}>
                    Open workpaper:{" "}
                    {String(
                      e.workpapers.find((w) => w.id === r.workpaperId)?.title ??
                        "Untitled workpaper",
                    )}{" "}
                    · version {r.workpaperVersion}
                  </button>
                ) : (
                  <p>
                    Workpaper {r.workpaperId} version {r.workpaperVersion}:
                    exact recorded pin is unavailable; no newer version
                    substituted.
                  </p>
                )}
              </div>
              <details>
                <summary>
                  Recorded procedure, correction and source pins
                </summary>
                <p>
                  Author: {r.actor || "Not recorded"} · Recorded at:{" "}
                  {r.recordedAt || "Not recorded"}
                </p>
                <p>Purpose: {r.purpose || "Not recorded"}</p>
                <p>
                  Procedure recorded as performed:{" "}
                  {r.procedure || "Not recorded"}
                </p>
                {r.correctionRationale && (
                  <p>Correction rationale: {r.correctionRationale}</p>
                )}
                <p>
                  Selection {r.selectionId} · Population {r.populationId} ·{" "}
                  {r.populationStatus} · Item basis {r.basis || "Not recorded"}
                </p>
                <p>
                  Artifact {r.artifactId} · SHA-256 {r.artifactSha256}
                </p>
                <p>
                  Procedure {r.taskId} · digest:{" "}
                  {r.taskDigest || "Not recorded"}
                </p>
                <p>
                  Workpaper {r.workpaperId} · version {r.workpaperVersion} ·
                  digest: {r.workpaperDigest || "Not recorded"}
                </p>
              </details>
            </article>
          ))}
        </>
      )}
    </section>
  );
}
