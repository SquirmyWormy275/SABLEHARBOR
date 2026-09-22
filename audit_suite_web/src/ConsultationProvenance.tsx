import type { Engagement, Row } from "./api";
import {
  consultationRelationLabels,
  resolveConsultationMessage,
} from "./companyConsultation";
import type { Consultation, MessagePin } from "./companyConsultation";
export function ConsultationProvenance({
  engagement: e,
  message,
  onPreview,
}: {
  engagement: Engagement;
  message: Row;
  onPreview: (kind: string, row: Row, reference?: Row) => void;
}) {
  const value = message.consultation as
    | (Consultation & {
        request_authorship?: string;
        relation?: string;
        source_support?: string;
        context_sha256?: string;
        source_manifest?: Record<string, unknown>[];
      })
    | undefined;
  if (!value) return null;
  const learner = message.role === "user";
  const contacts = e.people.filter((person) => person.id === message.person_id);
  const contact = contacts.length === 1 ? contacts[0] : null;
  function link(pin: MessagePin, label: string) {
    const match = resolveConsultationMessage(e, pin);
    return (
      <li key={label}>
        {label}: {pin.meeting_id} / {pin.message_id} · <code>{pin.sha256}</code>
        {match ? (
          <button
            type="button"
            onClick={() =>
              onPreview("meeting", match.meeting, {
                id: match.meeting.id,
                message_id: pin.message_id,
                sha256: pin.sha256,
              })
            }
          >
            Open exact {label.toLowerCase()}
          </button>
        ) : (
          <p>
            This historical message pin is not currently available for
            navigation.
          </p>
        )}
      </li>
    );
  }
  return (
    <details>
      <summary>
        {learner
          ? "Learner-requested company consultation"
          : "Company statement about an earlier exchange"}
      </summary>
      <p>
        {value.kind === "REFERRAL"
          ? "Referral to a company contact"
          : "Request concerning an earlier reply"}
      </p>
      {!learner && (
        <>
          <p>
            Responding contact:{" "}
            {contact
              ? String(contact.name ?? contact.id)
              : String(message.person_id ?? "Identity not recorded")}
            {contact?.title ? ` · ${String(contact.title)}` : ""}{" "}
            {message.person_id ? `(${String(message.person_id)})` : ""}
          </p>
          <p>
            {consultationRelationLabels[value.relation ?? ""] ??
              "Recorded company statement"}
          </p>
          <p>
            This is the contact's attributed statement, not verification that an
            earlier statement is true or false.
          </p>
          <p>Source support: {value.source_support ?? "Not recorded"}.</p>
        </>
      )}
      {Array.isArray(value.source_manifest) &&
        value.source_manifest.length > 0 && (
          <details>
            <summary>
              Original source context recorded with this statement
            </summary>
            <p>
              These metadata pins record the context supplied to the contact,
              not independent verification of their statement.
            </p>
            {value.source_manifest.map((source, index) => {
              const identity = source.source_identity as
                Record<string, unknown> | undefined;
              return (
                <div key={index}>
                  <dl>
                    {[
                      "company",
                      "branch",
                      "system",
                      "record",
                      "version",
                      "sha256",
                      "source_store_id",
                      "source_system_alias",
                      "registry_sha256",
                      "portfolio_qualification",
                    ].map(
                      (key) =>
                        identity?.[key] !== undefined && (
                          <div key={key}>
                            <dt>{key}</dt>
                            <dd>{String(identity[key])}</dd>
                          </div>
                        ),
                    )}
                  </dl>
                  <p>
                    Source reference:{" "}
                    {String(source.source_id ?? "Not recorded")}
                  </p>
                  {source.qualifiers !== undefined && (
                    <p>
                      Source qualifications: {JSON.stringify(source.qualifiers)}
                    </p>
                  )}
                </div>
              );
            })}
          </details>
        )}
      <ul>
        {value.question_ref && link(value.question_ref, "Question")}
        {value.response_ref && link(value.response_ref, "Reply")}
      </ul>
    </details>
  );
}

export function QueuedConsultation({ value }: { value: Consultation }) {
  return (
    <div>
      <p>Original learner-requested consultation: {value.kind}</p>
      <ul>
        {[
          ["Question", value.question_ref],
          ["Reply", value.response_ref],
        ].map(([label, pin]) =>
          pin && typeof pin !== "string" ? (
            <li key={String(label)}>
              {String(label)}: {pin.meeting_id} / {pin.message_id} · SHA256{" "}
              <code>{pin.sha256}</code>
            </li>
          ) : null,
        )}
      </ul>
      <p>
        Retry retains these exact references and the original target meeting; it
        does not select a newer reply.
      </p>
    </div>
  );
}
