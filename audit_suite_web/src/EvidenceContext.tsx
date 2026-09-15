import { useId, useRef, useState } from "react";
import type { Engagement } from "./api";
import {
  evidenceContextKey,
  recordedEvidenceContext,
  resolveEvidenceContextReference,
  type EvidenceContextReference,
  type EvidenceDraftSelection,
} from "./evidenceContext";
import "./evidenceContext.css";

export function EvidenceContext({
  engagement: e,
  artifactId,
  viewerId,
  onOpen,
  onStartDraft,
}: {
  engagement: Engagement;
  artifactId: string;
  viewerId: string;
  onOpen: (reference: EvidenceContextReference) => void;
  onStartDraft?: (selection: EvidenceDraftSelection) => void;
}) {
  const id = useId(),
    key = evidenceContextKey(e, viewerId, artifactId);
  const [hiddenKey, setHiddenKey] = useState<string | null>(null);
  const current = useRef({ e, key });
  current.current = { e, key };
  const context = recordedEvidenceContext(e, artifactId);
  if (!context)
    return <p>Recorded context is unavailable in this workspace.</p>;
  const hidden = hiddenKey === key;
  function open(ref: EvidenceContextReference) {
    if (
      current.current.key === key &&
      resolveEvidenceContextReference(current.current.e, ref)
    )
      onOpen(ref);
  }
  return (
    <aside className="evidence-context" aria-labelledby={`${id}-title`}>
      <div className="evidence-context-heading">
        <h3 id={`${id}-title`}>Recorded context and next actions</h3>
        <button
          type="button"
          aria-expanded={!hidden}
          aria-controls={`${id}-body`}
          onClick={() => setHiddenKey(hidden ? null : key)}
        >
          {hidden ? "Show recorded context" : "Hide recorded context"}
        </button>
      </div>
      {!hidden && (
        <div id={`${id}-body`}>
          <p>
            These are recorded relationships, not an assessment of sufficiency
            or effectiveness.
          </p>
          <p className="evidence-context-pin">
            {context.artifact.id} · SHA-256{" "}
            {String(context.artifact.sha256 ?? "Not supplied")}
          </p>
          <section aria-label="Recorded request purpose">
            <h4>Why it was requested</h4>
            {context.request ? (
              <>
                <p>
                  {String(context.request.purpose ?? "No purpose recorded.")}
                </p>
                <button
                  type="button"
                  onClick={() =>
                    open({ collection: "requests", id: context.request!.id })
                  }
                >
                  Open request {context.request.id}
                </button>
                {context.request.title && (
                  <p>{String(context.request.title)}</p>
                )}
              </>
            ) : (
              <p>
                No linked request is available. No purpose is inferred from the
                filename.
              </p>
            )}
          </section>
          <section aria-label="Declared relevance">
            <h4>Declared control relevance</h4>
            {context.declaredControls.map((control) => (
              <p key={control.id}>
                Source-declared:{" "}
                <button
                  type="button"
                  onClick={() =>
                    open({ collection: "controls", id: control.id })
                  }
                >
                  {control.id}
                </button>{" "}
                {String(control.title ?? control.name ?? "")}
              </p>
            ))}
            {context.requestedControl && (
              <p>
                Request-linked:{" "}
                <button
                  type="button"
                  onClick={() =>
                    open({
                      collection: "controls",
                      id: context.requestedControl!.id,
                    })
                  }
                >
                  {context.requestedControl.id}
                </button>{" "}
                {String(
                  context.requestedControl.title ??
                    context.requestedControl.name ??
                    "",
                )}
              </p>
            )}
            {!context.declaredControls.length && !context.requestedControl && (
              <p>No available scoped control link is recorded.</p>
            )}
            {context.declarationUnavailable && (
              <p>
                Some declared references are unavailable in the current scope.
              </p>
            )}
            <p>
              A declared relationship does not show that this original supports
              a procedure.
            </p>
          </section>
          <section aria-label="Related scoped procedure definitions">
            <h4>Related scoped procedures</h4>
            <p>Related by control only; evidence support is not established.</p>
            {context.procedures.length ? (
              <ul>
                {context.procedures.map((task) => (
                  <li key={task.id}>
                    <button
                      type="button"
                      onClick={() => open({ collection: "tasks", id: task.id })}
                    >
                      {task.id}
                    </button>
                    <p>
                      {String(
                        task.procedure ??
                          task.description ??
                          task.title ??
                          "No procedure text recorded.",
                      )}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p>
                No current procedure is explicitly related through these
                controls.
              </p>
            )}
          </section>
          <section aria-label="Exact workpaper citations">
            <h4>Workpaper versions citing this original</h4>
            <p>Citation records use, not acceptance or successful testing.</p>
            {context.citations.length ? (
              <ul>
                {context.citations.map((c) => (
                  <li key={`${c.paper.id}:${c.version}`}>
                    <button
                      type="button"
                      onClick={() =>
                        open({
                          collection: "workpapers",
                          id: c.paper.id,
                          version: c.version,
                        })
                      }
                    >
                      {c.paper.id} · version {c.version}
                    </button>
                    <p>
                      {c.taskIds.length
                        ? `Procedure IDs explicitly recorded in this version: ${c.taskIds.join(", ")}`
                        : "No available procedure IDs are recorded in this version."}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p>
                No exact workpaper version cites this original. This is not an
                adverse conclusion.
              </p>
            )}
          </section>
          {onStartDraft && context.canDraft && (
            <button
              type="button"
              onClick={() => {
                const latest = recordedEvidenceContext(
                  current.current.e,
                  artifactId,
                );
                if (current.current.key === key && latest?.canDraft)
                  onStartDraft({ artifactId });
              }}
            >
              Open workpaper draft
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
