import { EvidenceContext } from "./EvidenceContext";
import { evidenceContextKey, recordedEvidenceContext } from "./evidenceContext";
import RetainedPanel from "./RetainedPanel";
import PopulationLineage from "./PopulationLineage";
import { lineageReference } from "./populationLineage";
import SourceRecordCensus from "./SourceRecordCensus";
import { ConversationProvenance } from "./ConversationProvenance";
import { MeetingSourceContext } from "./MeetingSourceContext";
import { samePins, type SourcePin } from "./meetingSources";
import { compatibleWorkpaperValues, supports } from "./compatibility";
import { recordSequence } from "./recordSequence";
import { BackgroundWork } from "./BackgroundWork";
import { InvestigationContexts } from "./InvestigationContexts";
import { WorkStatus } from "./WorkStatus";
import { submitMeetingJob } from "./backgroundWork";
import { WorkpaperSupport } from "./WorkpaperSupport";
import { appendEvidenceReference } from "./workpaperSupport";
import { TableWorkspace } from "./TableWorkspace";
import CompanyPopulation from "./CompanyPopulation";
import { createDraftStore, type DraftKey } from "./draftContext";
import {
  createNavigationMemory,
  parseWorkspaceLink,
  workspaceLink,
  orientation,
} from "./navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  workpaperVersions,
  newWorkpaperVersion,
  canReviewWorkpaper,
  requestHasDelivery,
  artifactURL,
  command,
  human,
  normalize,
  request,
  setCSRF,
  str,
  type Bootstrap,
  type Engagement,
  type Row,
} from "./api";
import {
  ActionForm,
  Badge,
  Detail,
  Empty,
  Modal,
  Table,
  type Action,
  type Field,
} from "./components";
import Setup from "./Setup";
import CompanySources from "./CompanySources";
import SourceImpact from "./SourceImpact";
import InstructorKey from "./InstructorKey";
import BoundInstructorKey from "./BoundInstructorKey";
import WorkspaceSearch from "./WorkspaceSearch";
import CustomAuthoring from "./CustomAuthoring";
import SelectionImport from "./SelectionImport";
import SampleResponses from "./SampleResponses";
import ParentSupport from "./ParentSupport";
import TemporalCoverage from "./TemporalCoverage";
import ReviewDialog from "./ReviewDialog";
import { VoiceInput, SpeakButton } from "./Voice";
const sections = [
  ["kickoff", "Kickoff & scope"],
  ["controls", "Controls & tracker"],
  ["pbc", "PBC & evidence"],
  ["meetings", "Meetings · MRL"],
  ["people", "People"],
  ["populations", "Populations & samples"],
  ["notes", "Notes"],
  ["calendar", "Calendar & timeline"],
  ["findings", "Exceptions & remediation"],
  ["review", "Workpapers & review"],
] as const;
type Section = (typeof sections)[number][0];
const f = (
  name: string,
  label: string,
  type: Field["type"] = "text",
  required = true,
): Field => ({ name, label, type, required });
const select = (name: string, label: string, values: string[]): Field => ({
  ...f(name, label, "select"),
  options: values.map((value) => ({ value, label: human(value) })),
});
const linked = (name: string, label: string, rows: Row[]): Field => ({
  ...f(name, label, "select"),
  options: rows.map((r) => ({
    value: r.id,
    label: `${r.id} · ${str(r.title ?? r.name ?? r.subject ?? r.id)}`,
  })),
});
function NoteProvenance({
  note,
  engagement,
}: {
  note: Row;
  engagement: Engagement;
}) {
  const showRefs = (refs: unknown) =>
    Array.isArray(refs)
      ? refs.map((ref: Row, index: number) => {
          const message = engagement.meetings
            .flatMap((meeting) =>
              Array.isArray(meeting.messages)
                ? (meeting.messages as Row[])
                : [],
            )
            .find((m) => m.id === ref.message_id);
          const role =
            ref.speaker_role ??
            (message?.role === "user"
              ? "LEARNER"
              : message?.role === "assistant"
                ? "COMPANY"
                : "UNRESOLVED");
          const speaker =
            ref.speaker_id ?? message?.person_id ?? message?.actor;
          const person = engagement.people.find((p) => p.id === speaker);
          return (
            <li key={index}>
              <strong>
                {human(role)} speaker: {str(person?.name ?? speaker)}
              </strong>
              <p>
                Message: {str(ref.message_id)} · Span: {str(ref.start)}–
                {str(ref.end)}
              </p>
              <blockquote>
                {str(
                  ref.original_text ??
                    message?.content ??
                    "Original message not available in this view",
                )}
              </blockquote>
            </li>
          );
        })
      : null;
  return (
    <details>
      <summary>Sources and speakers</summary>
      <p>
        Extracted notes remain unconfirmed statements. Source attribution does
        not establish that a control operated.
      </p>
      <ul>{showRefs(note.source_refs)}</ul>
      {Array.isArray(note.attributed_bullets) &&
        (note.attributed_bullets as Row[]).map((bullet, index) => (
          <section key={index}>
            <h3>Extracted statement {index + 1}</h3>
            <p>{str(bullet.text)}</p>
            <small>{human(bullet.classification)}</small>
            <ul>{showRefs(bullet.source_refs)}</ul>
          </section>
        ))}
    </details>
  );
}
function Login({ onSuccess }: { onSuccess: () => void }) {
  const [credential, setCredential] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <main className="login">
      <img
        src="/brand/sable-harbor__primary-horizontal.svg"
        alt="Sable Harbor"
      />
      <p className="eyebrow">Audit training suite</p>
      <h1>
        Your engagement
        <br />
        starts here.
      </h1>
      <p>Sign in with the local access credential provided by your operator.</p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await request("/api/session", "POST", { credential });
            setCredential("");
            onSuccess();
          } catch (error) {
            setError((error as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Access credential
          <input
            type="password"
            autoComplete="current-password"
            value={credential}
            onChange={(e) => setCredential(e.target.value)}
            required
          />
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Signing in…" : "Enter workroom"}
        </button>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
      </form>
      <small>
        Private training environment · No real client communications
      </small>
    </main>
  );
}
function workpaperFields(e: Engagement): Field[] {
  return [
    f("title", "Workpaper title"),
    linked("control_id", "Control", e.controls),
    select("section", "Section", [
      "scope",
      "risk_assessment",
      "planning",
      "walkthrough",
      "populations",
      "testing",
      "roll_forward",
      "findings",
      "conclusions",
      "report_draft",
      "review_notes",
    ]),
    f("objective", "Objective", "textarea"),
    f("procedures", "Nature, timing and extent", "textarea"),
    f("evidence_ids", "Evidence references"),
    f("conclusion", "Conclusion and limitations", "textarea"),
  ];
}
type DetailContext = {
  row: Row;
  kind: string;
  sequence?: string[];
  returnTo?: DetailContext;
  focusVersion?: number;
  pinnedReference?: Row;
  returnToBoundSource?: boolean;
};
export default function App() {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null),
    [engagement, setEngagement] = useState<Engagement | null>(null),
    [section, setSection] = useState<Section>("kickoff"),
    [setup, setSetup] = useState(false),
    [unauthorized, setUnauthorized] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [action, setAction] = useState<Action | null>(null),
    [detail, setDetail] = useState<DetailContext | null>(null),
    [meetingId, setMeetingId] = useState(""),
    [message, setMessage] = useState(""),
    [query, setQuery] = useState(""),
    [framework, setFramework] = useState("all"),
    [uploadKind, setUploadKind] = useState("workpaper"),
    [uploadLink, setUploadLink] = useState(""),
    [experimentalConsent, setExperimentalConsent] = useState(false);
  const [evidenceHandoff, setEvidenceHandoff] = useState<{
    key: string;
    artifactId: string;
    detail: DetailContext;
  } | null>(null);
  const uploadRef = useRef<HTMLInputElement>(null);
  const navigationMemory = useRef(createNavigationMemory());
  const draftStore = useRef(createDraftStore());
  const navigationEpoch = useRef(0);
  const authorizedContext = useRef("");
  const currentEngagement = useRef<string | null>(null);
  const [sourceSelection, setSourceSelection] = useState<{
    key: string;
    pins: SourcePin[];
  }>({ key: "", pins: [] });
  const activeMeeting =
    engagement?.meetings.find((m) => m.id === meetingId) ??
    engagement?.meetings.find((m) => m.kind === "kickoff") ??
    engagement?.meetings[0];
  const sourceContext = JSON.stringify([
    bootstrap?.viewer.id,
    engagement?.id,
    engagement?.scope,
    engagement?.permissions,
    engagement?.company_source_binding,
    engagement?.evidence_acquisition,
    engagement?.simulated_at,
  ]);
  const meetingSourceKey = (meeting: Row | undefined) =>
    JSON.stringify([sourceContext, meeting?.id, meeting?.person_id]);
  const sourceSelectionKey = meetingSourceKey(activeMeeting);
  useEffect(() => {
    setSourceSelection((old) =>
      old.key === sourceSelectionKey
        ? old
        : { key: sourceSelectionKey, pins: [] },
    );
  }, [sourceSelectionKey]);
  const pendingSend = useRef<{
    engagement: string;
    sourceContext: string;
    command: Parameters<typeof submitMeetingJob>[1];
  } | null>(null);
  const listPosition = useRef({ section, query, framework });
  listPosition.current = { section, query, framework };
  function savePosition() {
    const current = listPosition.current;
    navigationMemory.current.save(current.section, {
      query: current.query,
      framework: current.framework,
      scrollTop: window.scrollY,
    });
  }
  function restorePosition(next: Section) {
    const saved = navigationMemory.current.restore(next);
    setSection(next);
    setQuery(saved.query);
    setFramework(saved.framework);
    requestAnimationFrame(() => window.scrollTo(0, saved.scrollTop));
  }
  const clearContext = useCallback(() => {
    pendingSend.current = null;
    setEvidenceHandoff(null);
    setSourceSelection({ key: "", pins: [] });
    navigationMemory.current.clear();
    draftStore.current.clear();
    authorizedContext.current = "";
    currentEngagement.current = null;
    setEngagement(null);
    setDetail(null);
    setAction(null);
    setMeetingId("");
    setMessage("");
    setUploadLink("");
    setUploadKind("workpaper");
    setExperimentalConsent(false);
    setQuery("");
    setFramework("all");
    setNotice("");
    setBusy(false);
    setSetup(false);
    if (uploadRef.current) uploadRef.current.value = "";
  }, []);
  const load = useCallback(async () => {
    const epoch = ++navigationEpoch.current;
    const search = location.search;
    const id = new URLSearchParams(search).get("engagement");
    if (id !== currentEngagement.current) clearContext();
    try {
      const b = await request<Bootstrap>("/api/bootstrap");
      if (epoch !== navigationEpoch.current) return;
      setCSRF(b.csrf_token);
      setBootstrap(b);
      setUnauthorized(false);
      setError("");
      const fetched = id
        ? normalize(
            await request<Engagement>(
              `/api/engagements/${encodeURIComponent(id)}`,
            ),
          )
        : null;
      if (epoch !== navigationEpoch.current) return;
      const resolved = parseWorkspaceLink(search, fetched);
      if (resolved.status !== "ready" || !fetched) {
        clearContext();
        if (resolved.status === "unavailable")
          setError(
            "This workspace link is unavailable. Return to engagements to choose accessible work.",
          );
        return;
      }
      currentEngagement.current = fetched.id;
      navigationMemory.current.activate(fetched, b.viewer);
      setEngagement(fetched);
      setSetup(false);
      const saved = navigationMemory.current.restore(resolved.location.section);
      setSection(resolved.location.section);
      setQuery(saved.query);
      setFramework(saved.framework);
      setDetail(null);
      if (resolved.location.object) {
        const object = resolved.location.object;
        const singular: Record<string, string> = {
          people: "person",
          controls: "control",
          requests: "request",
          artifacts: "artifact",
          populations: "population",
          selections: "selection",
          findings: "finding",
          workpapers: "workpaper",
          reviews: "review",
          meetings: "meeting",
          notes: "note",
          calendar: "calendar",
        };
        setDetail({
          row: fetched[object.kind].find((row) => row.id === object.id)!,
          kind: singular[object.kind],
        });
      }
      requestAnimationFrame(() => {
        if (epoch === navigationEpoch.current)
          window.scrollTo(0, saved.scrollTop);
      });
    } catch (e) {
      if (epoch !== navigationEpoch.current) return;
      clearContext();
      if (e instanceof ApiError && e.status === 401) setUnauthorized(true);
      else setError((e as Error).message);
    }
  }, [clearContext]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    const fn = () => {
      savePosition();
      void load();
    };
    window.addEventListener("popstate", fn);
    return () => window.removeEventListener("popstate", fn);
  }, [load]);
  useEffect(() => {
    if (!engagement || !bootstrap) return;
    const contextKey = JSON.stringify([
      bootstrap.viewer.id,
      [...bootstrap.viewer.roles].sort(),
      engagement.id,
      [...(engagement.permissions ?? [])].sort(),
      engagement.scope,
    ]);
    if (authorizedContext.current && authorizedContext.current !== contextKey) {
      ++navigationEpoch.current;
      setEvidenceHandoff(null);
      setAction(null);
      setDetail(null);
      setMessage("");
      setMeetingId("");
      setUploadLink("");
      setExperimentalConsent(false);
      setQuery("");
      setFramework("all");
      setBusy(false);
    }
    authorizedContext.current = contextKey;
    draftStore.current.activate({
      actorId: bootstrap.viewer.id,
      engagementId: engagement.id,
      roles: bootstrap.viewer.roles,
      permissions: engagement.permissions ?? [],
      scope: engagement.scope,
    });
    navigationMemory.current.activate(engagement, bootstrap.viewer);
    const collections: Record<string, Row[]> = {
      control: engagement.controls,
      task: engagement.tasks,
      person: engagement.people,
      request: engagement.requests,
      artifact: engagement.artifacts,
      population: engagement.populations,
      selection: engagement.selections,
      finding: engagement.findings,
      workpaper: engagement.workpapers,
      review: engagement.reviews,
      note: engagement.notes,
      meeting: engagement.meetings,
      calendar: engagement.calendar,
    };
    setDetail((previous) => {
      if (!previous) return null;
      if (
        previous.returnToBoundSource &&
        !engagement.permissions?.includes("instruct")
      )
        return null;
      const rows = (collections[previous.kind] ?? []).filter(
        (row) => row.id === previous.row.id,
      );
      if (rows.length !== 1) return null;
      if (
        previous.pinnedReference &&
        !lineageReference(engagement, previous.pinnedReference)
      )
        return null;
      if (
        previous.focusVersion !== undefined &&
        !workpaperVersions(rows[0]).some(
          (version) => version.version === previous.focusVersion,
        )
      )
        return null;
      return { ...previous, row: rows[0] };
    });
  }, [engagement, bootstrap]);
  useEffect(() => {
    if (!engagement || !["GENERATING", "VALIDATING"].includes(engagement.phase))
      return;
    const epoch = navigationEpoch.current;
    let cancelled = false;
    const timer = setInterval(() => {
      void request<Engagement>(
        `/api/engagements/${encodeURIComponent(engagement.id)}`,
      )
        .then((e) => {
          if (!cancelled && epoch === navigationEpoch.current)
            setEngagement((old) =>
              old && old.id === e.id && old.revision <= e.revision
                ? normalize(e)
                : old,
            );
        })
        .catch((e) => {
          if (!cancelled && epoch === navigationEpoch.current)
            setError(e.message);
        });
    }, 1500);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [engagement?.id, engagement?.phase]);
  function navigate(next: Section) {
    if (!engagement) return;
    savePosition();
    restorePosition(next);
    setDetail(null);
    history.pushState(
      {},
      "",
      workspaceLink({ engagement: engagement.id, section: next }),
    );
  }
  async function open(id: string) {
    savePosition();
    history.pushState(
      {},
      "",
      workspaceLink({ engagement: id, section: "kickoff" }),
    );
    await load();
  }
  async function act(
    kind: string,
    payload: Record<string, unknown>,
    afterFormalSave?: () => Promise<boolean>,
  ) {
    if (!engagement) return;
    const epoch = navigationEpoch.current;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const e = normalize(
        await command(engagement.id, engagement.revision, kind, payload),
      );
      const cleanupFailed = afterFormalSave
        ? !(await afterFormalSave())
        : false;
      if (epoch !== navigationEpoch.current) return;
      setEngagement(e);
      setAction(null);
      setNotice(
        cleanupFailed
          ? "Formal record saved. Personal draft cleanup failed; the retained draft must be reviewed before reuse."
          : "Saved to this engagement.",
      );
      return e;
    } catch (e) {
      if (epoch !== navigationEpoch.current) return;
      setError(
        e instanceof ApiError && e.status === 409
          ? "This engagement changed in another session. Refresh to review the latest version before saving again."
          : (e as Error).message,
      );
      throw e;
    } finally {
      if (epoch === navigationEpoch.current) setBusy(false);
    }
  }
  function run(kind: string, payload: Record<string, unknown>) {
    void act(kind, payload).catch(() => {});
  }
  function edit(
    title: string,
    kind: string,
    fields: Field[],
    initial?: Record<string, unknown>,
    description?: string,
  ) {
    setEvidenceHandoff(null);
    setAction({ title, kind, fields, initial, description });
  }
  async function create(payload: Record<string, unknown>) {
    const epoch = navigationEpoch.current;
    setBusy(true);
    setError("");
    try {
      let e = normalize(
        await request<Engagement>("/api/engagements", "POST", payload),
      );
      if (epoch !== navigationEpoch.current) return;
      currentEngagement.current = e.id;
      setEngagement(e);
      setSetup(false);
      history.pushState(
        {},
        "",
        `?engagement=${encodeURIComponent(e.id)}&view=kickoff`,
      );
      setSection("kickoff");
      e = normalize(await command(e.id, e.revision, "scenario.validate", {}));
      if (epoch !== navigationEpoch.current) return;
      currentEngagement.current = e.id;
      setEngagement(e);
      if (
        e.phase !== "INVALID" &&
        !((e.configuration as { selections?: Row[] })?.selections ?? []).some(
          (s) => s.authoring_mode === "CUSTOM",
        )
      ) {
        const built = normalize(
          await command(e.id, e.revision, "scenario.build", {}),
        );
        if (epoch === navigationEpoch.current) setEngagement(built);
      }
    } catch (e) {
      if (epoch !== navigationEpoch.current) return;
      setError((e as Error).message);
    } finally {
      if (epoch === navigationEpoch.current) setBusy(false);
    }
  }
  async function upload(file: File) {
    if (!engagement) return;
    const epoch = navigationEpoch.current;
    setBusy(true);
    setError("");
    try {
      const data = new FormData();
      data.set("file", file);
      data.set("kind", uploadKind);
      data.set("linked_id", uploadLink);
      data.set("expected_revision", String(engagement.revision));
      data.set("command_id", crypto.randomUUID());
      const uploaded = normalize(
        await request<Engagement>(
          `/api/engagements/${encodeURIComponent(engagement.id)}/uploads`,
          "POST",
          data,
        ),
      );
      if (epoch !== navigationEpoch.current) return;
      setEngagement(uploaded);
      setNotice("Original file retained with its submission history.");
    } catch (e) {
      if (epoch !== navigationEpoch.current) return;
      setError((e as Error).message);
    } finally {
      if (epoch === navigationEpoch.current) setBusy(false);
      if (epoch === navigationEpoch.current && uploadRef.current)
        uploadRef.current.value = "";
    }
  }
  if (unauthorized) return <Login onSuccess={() => void load()} />;
  if (!bootstrap)
    return (
      <main className="loading">
        <h1>Sable Harbor</h1>
        {error ? (
          <>
            <p role="alert">{error}</p>
            <button onClick={() => void load()}>Retry connection</button>
          </>
        ) : (
          <p role="status">Opening your workroom…</p>
        )}
      </main>
    );
  const draftKind = action?.kind;
  const draftPaper =
    draftKind === "workpaper.update"
      ? engagement?.workpapers.find(
          (p) => p.id === action?.initial?.workpaper_id,
        )
      : undefined;
  const actionDraft =
    action &&
    engagement &&
    bootstrap &&
    (engagement.permissions ?? []).some(
      (p) => p === "learn" || p === "instruct",
    ) &&
    (draftKind === "note.create" ||
      draftKind === "workpaper.add" ||
      (draftKind === "workpaper.update" && draftPaper))
      ? {
          store: draftStore.current,
          remote: supports(bootstrap.capabilities, "personal_drafts"),
          key: {
            actorId: bootstrap.viewer.id,
            engagementId: engagement.id,
            kind: draftKind,
            objectId: draftPaper?.id ?? "new",
            baseVersion: draftPaper
              ? String(workpaperVersions(draftPaper).at(-1)?.version ?? "1")
              : "NEW",
          } as DraftKey,
          initial: compatibleWorkpaperValues(
            action.kind,
            draftPaper
              ? newWorkpaperVersion(draftPaper)
              : (action.initial ?? {}),
            bootstrap.capabilities,
          ),
        }
      : undefined;
  const e = engagement;
  const renderEpoch = navigationEpoch.current;
  const controlLink = (row: Row) => {
    const id = str(row.control_id);
    const control = e?.controls.find((c) => c.id === id);
    return control ? (
      <button
        className="text-link"
        onClick={() => setDetail({ row: control, kind: "control" })}
      >
        {id}
      </button>
    ) : (
      id
    );
  };
  const ownerLink = (row: Row) => {
    const id = str(
      row.owner_id ??
        row.person_id ??
        (Array.isArray(row.owner_ids) ? row.owner_ids[0] : undefined),
    );
    const person = e?.people.find((p) => p.id === id);
    return person ? (
      <button
        className="text-link"
        onClick={() => setDetail({ row: person, kind: "person" })}
      >
        {str(person.name)}
      </button>
    ) : (
      str(row.owner ?? row.owner_id ?? row.person_id ?? row.owner_ids)
    );
  };
  const download = (row: Row) =>
    e ? (
      <a
        className="text-link"
        href={artifactURL(e.id, str(row.artifact_id ?? row.id))}
      >
        Download original
      </a>
    ) : null;
  const canTrain = bootstrap.viewer.roles.some((r) =>
    ["instructor", "trainer", "admin", "administrator"].includes(
      r.toLowerCase(),
    ),
  );
  const selectedSources =
    sourceSelection.key === sourceSelectionKey &&
    bootstrap.capabilities.company_message_sources
      ? sourceSelection.pins
      : [];
  const messages = Array.isArray(activeMeeting?.messages)
    ? (activeMeeting.messages as Row[])
    : [];
  const meetingView = e ? (
    <div className="meeting-layout">
      <aside>
        <h3>Meeting record</h3>
        {e.meetings.map((m) => (
          <button
            key={m.id}
            className={activeMeeting?.id === m.id ? "current" : ""}
            onClick={() => setMeetingId(m.id)}
          >
            <strong>{str(m.title ?? m.subject ?? m.id)}</strong>
            <small>
              {human(m.status)} · {str(m.simulated_at ?? m.scheduled_at)}
            </small>
          </button>
        ))}
      </aside>
      <section className="conversation">
        <header>
          <p className="eyebrow">
            {section === "kickoff"
              ? "Engagement kickoff"
              : "Control-owner conversation"}
          </p>
          <h2>
            {str(
              activeMeeting?.title ??
                activeMeeting?.subject ??
                "Open the meeting",
            )}
          </h2>
          {activeMeeting && (
            <p>
              {ownerLink(activeMeeting)} · {controlLink(activeMeeting)}
            </p>
          )}
        </header>
        <div className="messages" role="log" aria-live="polite">
          {messages.length ? (
            messages.map((m, i) => (
              <article
                key={m.id ?? i}
                className={
                  ["learner", "user"].includes(String(m.role)) ? "learner" : ""
                }
              >
                <div>
                  <strong>{str(m.speaker_name ?? m.speaker ?? m.role)}</strong>
                  <Badge>{human(m.claim_type ?? "statement")}</Badge>
                </div>
                <p>{str(m.content ?? m.text)}</p>
                <ConversationProvenance
                  engagement={e}
                  message={m}
                  onPreview={(kind, row) => setDetail({ kind, row })}
                />
                {m.role === "assistant" && (
                  <SpeakButton
                    engagement={e.id}
                    message={m.id}
                    enabled={!!e.capabilities.voice}
                  />
                )}

                {!!m.source_message_id && (
                  <small>Source: {str(m.source_message_id)}</small>
                )}
              </article>
            ))
          ) : (
            <Empty title="The conversation is ready when you are">
              Messages, requests and resulting notes will be retained here.
            </Empty>
          )}
        </div>
        {activeMeeting ? (
          <form
            className="message-form"
            onSubmit={async (event) => {
              event.preventDefault();
              if (bootstrap.capabilities.background_jobs) {
                const pending = pendingSend.current;
                if (
                  pending &&
                  (pending.engagement !== e.id ||
                    pending.sourceContext !== sourceContext ||
                    pending.command.payload.meeting_id !== activeMeeting.id ||
                    pending.command.payload.content !== message ||
                    !samePins(
                      pending.command.payload.source_records ?? [],
                      selectedSources,
                    ))
                ) {
                  setError(
                    "The previous send has an unconfirmed outcome. Inspect background work or restore the queued question before retrying.",
                  );
                  return;
                }
                const envelope = pending?.command ?? {
                  command_id: crypto.randomUUID(),
                  expected_revision: e.revision,
                  kind: "meeting.message" as const,
                  payload: {
                    meeting_id: activeMeeting.id,
                    content: message,
                    ...(selectedSources.length
                      ? { source_records: structuredClone(selectedSources) }
                      : {}),
                  },
                };
                pendingSend.current = {
                  engagement: e.id,
                  sourceContext,
                  command: envelope,
                };
                setBusy(true);
                setError("");
                try {
                  const job = await submitMeetingJob(e.id, envelope);
                  if (renderEpoch !== navigationEpoch.current) return;
                  pendingSend.current = null;
                  setMessage((current) =>
                    current === envelope.payload.content ? "" : current,
                  );
                  setSourceSelection((current) =>
                    current.key === sourceSelectionKey &&
                    samePins(
                      current.pins,
                      envelope.payload.source_records ?? [],
                    )
                      ? { key: sourceSelectionKey, pins: [] }
                      : current,
                  );
                  setNotice(
                    `Company reply ${job.status.toLowerCase()}. You can continue working; inspect background work for its status.`,
                  );
                } catch (error) {
                  if (renderEpoch === navigationEpoch.current)
                    setError(
                      `${(error as Error).message} The question is retained here; retry reuses the same request.`,
                    );
                } finally {
                  if (renderEpoch === navigationEpoch.current) setBusy(false);
                }
                return;
              }
              try {
                const saved = await act("meeting.message", {
                  meeting_id: activeMeeting.id,
                  content: message,
                  ...(selectedSources.length
                    ? { source_records: structuredClone(selectedSources) }
                    : {}),
                });
                if (saved && renderEpoch === navigationEpoch.current) {
                  setMessage((current) => (current === message ? "" : current));
                  setSourceSelection((current) =>
                    current.key === sourceSelectionKey &&
                    samePins(current.pins, selectedSources)
                      ? { key: sourceSelectionKey, pins: [] }
                      : current,
                  );
                }
              } catch {}
            }}
          >
            <label>
              Ask the owner
              <textarea
                aria-label="Ask the owner"
                required
                rows={3}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Ask about the process, changes, population or supporting records…"
              />
            </label>
            {bootstrap.capabilities.company_message_sources &&
              Boolean(activeMeeting.person_id) && (
                <MeetingSourceContext
                  key={sourceSelectionKey}
                  engagement={e}
                  personId={str(activeMeeting.person_id)}
                  pins={selectedSources}
                  onChange={(pins) =>
                    setSourceSelection({ key: sourceSelectionKey, pins })
                  }
                />
              )}
            <VoiceInput
              engagement={e.id}
              enabled={!!e.capabilities.voice}
              onConfirm={(text) => {
                if (renderEpoch === navigationEpoch.current) setMessage(text);
              }}
            />
            <div>
              {pendingSend.current && !busy && (
                <p>
                  A send is unconfirmed. Check background work before composing
                  a replacement.
                  <button
                    type="button"
                    onClick={() => {
                      const pending = pendingSend.current;
                      if (pending) {
                        if (pending.sourceContext !== sourceContext) {
                          setError(
                            "The source context changed. Inspect the original queued question; reselect sources before creating a new command.",
                          );
                          return;
                        }
                        if (
                          (message &&
                            message !== pending.command.payload.content) ||
                          (selectedSources.length &&
                            !samePins(
                              selectedSources,
                              pending.command.payload.source_records ?? [],
                            ))
                        ) {
                          setError(
                            "Newer composer text or source selections are present. Keep them, or explicitly clear them before restoring the original queued question.",
                          );
                          return;
                        }
                        const target = e.meetings.find(
                          (m) => m.id === pending.command.payload.meeting_id,
                        );
                        if (!target) return;
                        setMeetingId(target.id);
                        setMessage(pending.command.payload.content);
                        setSourceSelection({
                          key: meetingSourceKey(target),
                          pins: structuredClone(
                            pending.command.payload.source_records ?? [],
                          ),
                        });
                      }
                    }}
                  >
                    Restore unconfirmed question
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      pendingSend.current = null;
                      setNotice(
                        "Local retry cleared. Any accepted background work still runs and remains in its history.",
                      );
                    }}
                  >
                    Clear local retry after inspection
                  </button>
                </p>
              )}
              <span className="hint">
                Statements remain attributed. A conversation does not complete a
                test.
              </span>
              <button className="primary" disabled={busy || !message.trim()}>
                Send message
              </button>
            </div>
          </form>
        ) : (
          <button
            className="primary"
            disabled={busy || !["READY", "KICKOFF", "ACTIVE"].includes(e.phase)}
            onClick={() => run("kickoff.start", {})}
          >
            Begin kickoff meeting
          </button>
        )}
      </section>
    </div>
  ) : null;
  const neighbors =
    e && detail?.sequence
      ? recordSequence(e, detail.kind, detail.sequence, detail.row.id)
      : null;
  return (
    <TableWorkspace
      key={JSON.stringify([
        bootstrap.viewer.id,
        bootstrap.viewer.roles,
        e?.id,
        e?.permissions,
        e?.scope,
      ])}
    >
      <div className="app">
        <a href="#main" className="skip">
          Skip to workspace
        </a>
        <aside className="rail">
          <a href="/" className="brand" aria-label="Sable Harbor home">
            <img
              src="/brand/sable-harbor__reverse-horizontal.svg"
              alt="Sable Harbor"
            />
          </a>
          <div className="rail-label">Audit training suite</div>
          <button
            className="engagement-switch"
            onClick={() => {
              ++navigationEpoch.current;
              clearContext();
              history.pushState({}, "", "/");
            }}
          >
            <span>Engagements</span>
            <strong>{e?.title ?? "Your workroom"}</strong>
            <span>↗</span>
          </button>
          <nav aria-label="Engagement workspace">
            {sections.map(([id, label], i) => (
              <button
                key={id}
                disabled={!e || setup}
                className={e && section === id && !setup ? "active" : ""}
                onClick={() => navigate(id)}
              >
                <span>{String(i + 1).padStart(2, "0")}</span>
                {label}
                {id === "pbc" && e?.requests.some((r) => r.unread) && (
                  <b className="unread" aria-label="New evidence" />
                )}
              </button>
            ))}
          </nav>
          <footer>
            <span className="avatar">
              {bootstrap.viewer.display_name.slice(0, 1)}
            </span>
            <div>
              <strong>{bootstrap.viewer.display_name}</strong>
              <small>{bootstrap.viewer.roles.join(" · ")}</small>
            </div>
            <button
              aria-label="Sign out"
              onClick={() => {
                void request("/api/logout", "POST", {})
                  .then(() => {
                    ++navigationEpoch.current;
                    clearContext();
                    setBootstrap(null);
                    setUnauthorized(true);
                  })
                  .catch((err) => setError(err.message));
              }}
            >
              ↪
            </button>
          </footer>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <div>
              <span className="status-dot" />
              Fictional training environment
            </div>
            {e && (
              <div>
                Simulation date{" "}
                <strong>
                  {new Intl.DateTimeFormat(undefined, {
                    dateStyle: "medium",
                    timeZone: str(e.scope.timezone ?? "UTC"),
                  }).format(new Date(str(e.simulated_at)))}{" "}
                  · {str(e.scope.timezone ?? "UTC")}
                </strong>
                <button onClick={() => navigate("calendar")}>Calendar ↗</button>
              </div>
            )}
            <span>
              Workroom /{" "}
              {setup
                ? "New engagement"
                : e
                  ? sections.find((s) => s[0] === section)?.[1]
                  : "Engagements"}
            </span>
          </header>
          {e && (
            <div
              className="workspace-orientation"
              aria-label="Current engagement context"
            >
              <strong>{e.title}</strong>
              {Boolean(e.company_source_binding) && (
                <span>
                  Company: {str((e.company_source_binding as Row).company)} ·
                  Branch: {str((e.company_source_binding as Row).branch)}
                </span>
              )}
              <span>
                Boundary:{" "}
                {orientation(e, bootstrap.viewer).boundaries.join(" · ")}
              </span>
              <span>
                Period: {e.scope.period_start} — {e.scope.period_end} ·{" "}
                {e.scope.report_type}
              </span>
              <span>
                Signed in: {bootstrap.viewer.display_name} ·{" "}
                {bootstrap.viewer.roles.join(" · ")}
              </span>
              <span>
                Engagement permissions:{" "}
                {(e.permissions ?? []).join(" · ") || "None reported"}
              </span>
            </div>
          )}
          {error && (
            <div className="alert error" role="alert">
              <span>{error}</span>
              <button onClick={() => (e ? void open(e.id) : void load())}>
                Refresh
              </button>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                ✕
              </button>
            </div>
          )}
          {notice && (
            <div className="alert success" role="status">
              <span>{notice}</span>
              <button
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                ✕
              </button>
            </div>
          )}
          {e && !setup && (
            <WorkspaceSearch
              engagement={e}
              viewerId={bootstrap.viewer.id}
              onPreview={(kind, row) => setDetail({ kind, row })}
              onNavigate={navigate}
            />
          )}
          <div id="main" tabIndex={-1}>
            {e && !setup && bootstrap.capabilities.workspace_contexts && (
              <InvestigationContexts
                engagement={e}
                viewerId={bootstrap.viewer.id}
                onPreview={(kind, row) => setDetail({ kind, row })}
              />
            )}
            {e && !setup && bootstrap.capabilities.background_jobs && (
              <details className="panel background-work-panel">
                <summary>Company replies and background work</summary>
                <BackgroundWork
                  engagement={e}
                  viewerId={bootstrap.viewer.id}
                  onInspect={(kind) =>
                    navigate(
                      kind === "company.census.collect"
                        ? "populations"
                        : "meetings",
                    )
                  }
                  onCompleted={() => {
                    const epoch = navigationEpoch.current;
                    void request<Engagement>(
                      `/api/engagements/${encodeURIComponent(e.id)}`,
                    )
                      .then((next) => {
                        if (
                          epoch === navigationEpoch.current &&
                          currentEngagement.current === e.id
                        )
                          setEngagement((previous) =>
                            previous?.id === e.id &&
                            previous.revision <= next.revision
                              ? normalize(next)
                              : previous,
                          );
                      })
                      .catch((error) => {
                        if (epoch === navigationEpoch.current)
                          setError((error as Error).message);
                      });
                  }}
                />
              </details>
            )}
            {setup ? (
              <Setup
                bootstrap={bootstrap}
                busy={busy}
                onCreate={create}
                onCancel={() => setSetup(false)}
              />
            ) : !e ? (
              <main className="workspace">
                <div className="page-heading">
                  <div>
                    <p className="eyebrow">
                      Sable Harbor / Engagement register
                    </p>
                    <h1>Work begins with a question.</h1>
                    <p>Resume an engagement or establish a new scope.</p>
                  </div>
                  {canTrain && (
                    <button className="primary" onClick={() => setSetup(true)}>
                      New engagement +
                    </button>
                  )}
                </div>
                {bootstrap.engagements.length ? (
                  <Table
                    memoryKey="engagements"
                    rows={bootstrap.engagements}
                    onOpen={(r) => void open(r.id)}
                    columns={[
                      { key: "title", label: "Engagement" },
                      { key: "discipline", label: "Discipline" },
                      { key: "phase", label: "Stage" },
                      { key: "simulated_at", label: "Simulation date" },
                    ]}
                  />
                ) : (
                  <Empty title="No engagements assigned">
                    {canTrain
                      ? "Create an engagement to choose the discipline, scenario and scope."
                      : "Your trainer can assign an engagement to this account."}
                  </Empty>
                )}
              </main>
            ) : (
              <main className="workspace">
                <div className="page-heading">
                  <div>
                    <p className="eyebrow">
                      {e.title} / {e.discipline}
                    </p>
                    <h1>{sections.find((s) => s[0] === section)?.[1]}</h1>
                    <p>
                      {section === "controls"
                        ? "Track the work performed. Record conclusions separately."
                        : section === "pbc"
                          ? "Requests, original files and every round of support."
                          : section === "review"
                            ? "Assemble your work. Preserve the complete review trail."
                            : "A connected record of your engagement."}
                    </p>
                  </div>
                  <Badge>{human(e.phase)}</Badge>
                </div>
                <CustomAuthoring engagement={e} busy={busy} onCommand={run} />
                {e.permissions?.includes("instruct") &&
                  (e.trainer_encounter_counts?.length ?? 0) > 0 && (
                    <section aria-label="Trainer encounter allocation">
                      <h2>Planned encounters</h2>
                      {e.trainer_encounter_counts?.map((item) => (
                        <p key={item.option_id}>
                          {item.option_id}: approximately {item.planned}{" "}
                          affected initial requests from {item.eligible}{" "}
                          eligible {human(item.basis).toLowerCase()} encounters.{" "}
                          {item.excluded} excluded for unresolved participants.
                          Follow-ups remain part of the initial encounter.
                        </p>
                      ))}
                    </section>
                  )}
                {e.generation &&
                  [
                    "CONFIGURING",
                    "GENERATING",
                    "VALIDATING",
                    "INVALID",
                    "FAILED",
                  ].includes(e.phase) && (
                    <section className="generation">
                      <h2>
                        {e.generation.stage ?? "Preparing the engagement"}
                      </h2>
                      <p>{human(e.generation.state)}</p>
                      {e.generation.total !== undefined && (
                        <progress
                          max={e.generation.total}
                          value={e.generation.completed ?? 0}
                        />
                      )}
                      <ul>
                        {e.generation.errors?.map((err) => (
                          <li key={err}>{err}</li>
                        ))}
                      </ul>
                      <div className="actions">
                        <button
                          disabled={busy}
                          onClick={() => run("scenario.validate", {})}
                        >
                          Validate configuration
                        </button>
                        <button
                          disabled={busy}
                          onClick={() => run("generation.retry", {})}
                        >
                          {e.scope_reconciliation_required
                            ? "Build revised scope"
                            : "Retry generation"}
                        </button>
                        <button
                          disabled={busy}
                          onClick={() => run("generation.cancel", {})}
                        >
                          Cancel generation
                        </button>
                      </div>
                    </section>
                  )}
                {section === "kickoff" && (
                  <>
                    <div className="scope-strip">
                      <div>
                        <small>Programs</small>
                        <strong>{e.scope.programs?.join(" + ")}</strong>
                      </div>
                      <div>
                        <small>Report basis</small>
                        <strong>{e.scope.report_type}</strong>
                      </div>
                      <div>
                        <small>Period / assessment date</small>
                        <strong>
                          {e.scope.period_start} — {e.scope.period_end}
                        </strong>
                      </div>
                      <div>
                        <small>Boundaries</small>
                        <strong>{e.scope.boundaries?.join(", ")}</strong>
                      </div>
                      <button
                        onClick={() =>
                          edit(
                            "Propose scope revision",
                            "scope.update",
                            [
                              f("rationale", "Reason for revision", "textarea"),
                              f("period_start", "Period starts", "date"),
                              f("period_end", "Period ends", "date"),
                              f("timezone", "Engagement timezone (IANA)"),
                              f("fieldwork_start", "Fieldwork begins", "date"),
                              f("programs", "Programs, comma separated"),
                              f("boundaries", "Boundaries, comma separated"),
                            ],
                            {
                              ...e.scope,
                              programs: e.scope.programs.join(", "),
                              boundaries: e.scope.boundaries.join(", "),
                            },
                            "Earlier work remains bound to its original scope version.",
                          )
                        }
                      >
                        Revise scope
                      </button>
                    </div>
                    {meetingView}
                  </>
                )}
                {section === "controls" && (
                  <>
                    {bootstrap.capabilities.work_status && (
                      <WorkStatus
                        key={e.id}
                        engagement={e}
                        onPreview={(kind, row) => setDetail({ kind, row })}
                      />
                    )}
                    <TemporalCoverage
                      engagement={e}
                      busy={busy}
                      onCommand={act}
                    />
                    <div className="actions">
                      <label>
                        Program view
                        <select
                          value={framework}
                          onChange={(event) => setFramework(event.target.value)}
                        >
                          <option value="all">All shared work</option>
                          {e.scope.programs.map((p) => (
                            <option key={p}>{p}</option>
                          ))}
                        </select>
                      </label>
                      <button
                        onClick={() =>
                          edit("Add procedure", "task.create", [
                            f("title", "Procedure / objective"),
                            linked("control_id", "Control", e.controls),
                            select("test_type", "Test type", [
                              "TOD",
                              "IMPLEMENTATION",
                              "TOE",
                              "SUBSTANTIVE",
                              "INTERIM",
                              "ROLL_FORWARD",
                              "OTHER",
                            ]),
                            f(
                              "rationale",
                              "Purpose and methodology",
                              "textarea",
                            ),
                          ])
                        }
                      >
                        Add procedure
                      </button>
                    </div>
                    <div className="progress-strip">
                      <span>
                        <b>
                          {
                            e.tasks.filter(
                              (t) =>
                                String(t.status).toUpperCase() === "COMPLETE",
                            ).length
                          }
                        </b>{" "}
                        /{" "}
                        {
                          e.tasks.filter(
                            (t) =>
                              String(t.status).toUpperCase() !==
                              "NOT_APPLICABLE",
                          ).length
                        }{" "}
                        tasks reported complete
                      </span>
                      <span>
                        <b>{e.requests.filter(requestHasDelivery).length}</b> /{" "}
                        {e.requests.length} requests received
                      </span>
                      <span>Progress is not assurance.</span>
                    </div>
                    <Table
                      memoryKey="procedures"
                      rows={e.tasks.filter(
                        (t) =>
                          framework === "all" ||
                          (Array.isArray(t.frameworks)
                            ? t.frameworks
                            : []
                          ).includes(framework),
                      )}
                      columns={[
                        {
                          key: "id",
                          label: "Task",
                          render: (r) => (
                            <button
                              className="text-link"
                              onClick={() =>
                                edit(
                                  "Update task",
                                  "task.update",
                                  [
                                    select("status", "Reported status", [
                                      "NOT_STARTED",
                                      "IN_PROGRESS",
                                      "COMPLETE",
                                      "NOT_APPLICABLE",
                                    ]),
                                    select("conclusion", "Test conclusion", [
                                      "NOT_RUN",
                                      "PASS",
                                      "FAIL",
                                      "LIMITATION",
                                      "NOT_APPLICABLE",
                                    ]),
                                    f(
                                      "rationale",
                                      "Rationale / notes",
                                      "textarea",
                                    ),
                                  ],
                                  {
                                    task_id: r.id,
                                    status: r.status,
                                    conclusion: r.conclusion,
                                    rationale: r.rationale,
                                  },
                                )
                              }
                            >
                              {r.id}
                            </button>
                          ),
                        },
                        { key: "title", label: "Procedure" },
                        {
                          key: "control_id",
                          label: "Control",
                          render: controlLink,
                        },
                        { key: "owner_id", label: "Owner", render: ownerLink },
                        {
                          key: "test_type",
                          label: "Work type",
                          render: (r) => str(r.test_type ?? r.kind),
                        },
                        {
                          key: "status",
                          label: "Reported status",
                          render: (r) => <Badge>{human(r.status)}</Badge>,
                        },
                        { key: "conclusion", label: "Conclusion" },
                        {
                          key: "note",
                          label: "Notes",
                          render: (r) => str(r.note ?? r.rationale ?? r.notes),
                        },
                      ]}
                    />
                    <h2>Common control register</h2>
                    <Table
                      memoryKey="controls"
                      rows={e.controls}
                      onOpen={(r, sequence) =>
                        setDetail({ row: r, kind: "control", sequence })
                      }
                      columns={[
                        { key: "id", label: "Control" },
                        { key: "title", label: "Control description" },
                        {
                          key: "owner_ids",
                          label: "Owners",
                          render: ownerLink,
                        },
                        { key: "frameworks", label: "Programs" },
                      ]}
                    />
                  </>
                )}
                {bootstrap.capabilities.company_sources && (
                  <RetainedPanel
                    key={sourceContext + ":company-browser"}
                    active={section === "pbc"}
                  >
                    <CompanySources
                      key={e.id}
                      engagement={e}
                      busy={busy}
                      onCommand={act}
                    />
                  </RetainedPanel>
                )}
                {section === "pbc" && (
                  <>
                    {bootstrap.capabilities.company_sources && (
                      <>
                        {bootstrap.capabilities.company_source_impact !==
                          false && (
                          <SourceImpact
                            key={e.id + ":impact"}
                            engagement={e}
                            onPreview={(kind, row) => setDetail({ kind, row })}
                          />
                        )}
                      </>
                    )}
                    <div className="actions">
                      <button
                        className="primary"
                        onClick={() =>
                          edit("Issue evidence request", "pbc.create", [
                            f("title", "Requested item"),
                            linked("control_id", "Control", e.controls),
                            linked("person_id", "Evidence owner", e.people),
                            f(
                              "purpose",
                              "Purpose and expected support",
                              "textarea",
                            ),
                            f("due_at", "Due date", "date"),
                            f("period_start", "Coverage starts", "date"),
                            f("period_end", "Coverage ends", "date"),
                          ])
                        }
                      >
                        New PBC request +
                      </button>
                      <button
                        onClick={() =>
                          run("review.export", { edition: "evidence" })
                        }
                      >
                        Export evidence manifest & files
                      </button>
                    </div>
                    <Table
                      memoryKey="requests"
                      rows={e.requests}
                      onOpen={(r, sequence) =>
                        setDetail({ row: r, kind: "request", sequence })
                      }
                      columns={[
                        { key: "id", label: "PBC" },
                        { key: "title", label: "Request" },
                        {
                          key: "control_id",
                          label: "Control",
                          render: controlLink,
                        },
                        { key: "owner_id", label: "Owner", render: ownerLink },
                        { key: "due_at", label: "Due" },
                        {
                          key: "status",
                          label: "Request status",
                          render: (r) => <Badge>{human(r.status)}</Badge>,
                        },
                        { key: "round", label: "Round" },
                      ]}
                    />
                    <h2>Original evidence files</h2>
                    <Table
                      memoryKey="artifacts"
                      rows={e.artifacts.filter((a) => a.kind !== "workpaper")}
                      onOpen={(r, sequence) =>
                        setDetail({ row: r, kind: "artifact", sequence })
                      }
                      columns={[
                        { key: "name", label: "Original file" },
                        { key: "request_id", label: "PBC" },
                        { key: "version", label: "Version" },
                        { key: "covered_period", label: "Effective coverage" },
                        { key: "received_at", label: "Received" },
                        { key: "id", label: "File", render: download },
                      ]}
                    />
                    <UploadControls
                      kind={uploadKind}
                      setKind={setUploadKind}
                      link={uploadLink}
                      setLink={setUploadLink}
                      requests={e.requests}
                      inputRef={uploadRef}
                      busy={busy}
                      onFile={upload}
                    />
                  </>
                )}
                {section === "meetings" && (
                  <>
                    <div className="actions">
                      <button
                        className="primary"
                        onClick={() =>
                          edit(
                            "Request an owner meeting",
                            "meeting.create",
                            [
                              f("title", "Subject"),
                              linked("control_id", "Control", e.controls),
                              linked("person_id", "Participant", e.people),
                              select("mode", "Meeting mode", [
                                "immediate",
                                "scheduled",
                              ]),
                              f(
                                "scheduled_at",
                                "Scheduled date",
                                "date",
                                false,
                              ),
                              f(
                                "purpose",
                                "Topics and requested support",
                                "textarea",
                              ),
                            ],
                            { mode: "immediate" },
                          )
                        }
                      >
                        Request meeting +
                      </button>
                    </div>
                    {meetingView}
                  </>
                )}
                {section === "people" && (
                  <Table
                    memoryKey="people"
                    rows={e.people}
                    onOpen={(r, sequence) =>
                      setDetail({ row: r, kind: "person", sequence })
                    }
                    columns={[
                      { key: "name", label: "Person" },
                      { key: "title", label: "Role" },
                      { key: "department", label: "Team" },
                      { key: "location", label: "Location" },
                      { key: "control_ids", label: "Responsibilities" },
                      { key: "effective_from", label: "Effective from" },
                    ]}
                  />
                )}
                {bootstrap.capabilities.company_source_census && (
                  <div hidden={section !== "populations"}>
                    <SourceRecordCensus
                      engagement={e}
                      viewerId={bootstrap.viewer.id}
                      busy={busy}
                      backgroundKinds={bootstrap.background_command_kinds ?? []}
                      onCommand={act}
                    />
                  </div>
                )}
                {section === "populations" && (
                  <>
                    {bootstrap.capabilities.company_sources &&
                      bootstrap.capabilities.company_populations !== false && (
                        <CompanyPopulation
                          key={e.id + ":population"}
                          engagement={e}
                          busy={busy}
                          onCommand={act}
                        />
                      )}
                    <ParentSupport engagement={e} busy={busy} onCommand={run} />
                    <div className="actions">
                      <button
                        onClick={() =>
                          edit("Select population items", "population.select", [
                            linked(
                              "population_id",
                              "Source population",
                              e.populations,
                            ),
                            select("method", "Selection method", [
                              "manual",
                              "simple_random",
                              "systematic",
                              "stratified",
                              "entire_population",
                              "nested",
                            ]),
                            f(
                              "selected_ids",
                              "Selected IDs, one per line",
                              "textarea",
                              false,
                            ),
                            f("size", "Requested sample size", "number", false),
                            f("seed", "Selection seed", "text", false),
                            f(
                              "purpose",
                              "Purpose and methodology rationale",
                              "textarea",
                            ),
                            f(
                              "parent_selection_id",
                              "Parent selection ID",
                              "text",
                              false,
                            ),
                          ])
                        }
                      >
                        Make selection
                      </button>
                      <button
                        onClick={() =>
                          edit(
                            "Request support for selected items",
                            "pbc.create",
                            [
                              linked("selection_id", "Selection", e.selections),
                              linked("person_id", "Evidence owner", e.people),
                              f("title", "Requested support"),
                              f("purpose", "Purpose", "textarea"),
                              f("due_at", "Due date", "date"),
                            ],
                          )
                        }
                      >
                        Request selected-item support
                      </button>
                      <button
                        onClick={() =>
                          edit(
                            "Sampling calculation",
                            "population.calculate",
                            [
                              select("method", "Calculation method", [
                                "zero_deviation_attribute",
                                "manual_methodology",
                              ]),
                              f("population_size", "Population size", "number"),
                              f("confidence", "Confidence (0–1)", "number"),
                              f(
                                "tolerable_rate",
                                "Tolerable deviation (0–1)",
                                "number",
                              ),
                              f(
                                "rationale",
                                "Methodology and assumptions",
                                "textarea",
                              ),
                            ],
                            undefined,
                            "This is a mathematical training helper. Sample size does not establish professional sufficiency.",
                          )
                        }
                      >
                        Sampling calculator
                      </button>
                    </div>
                    <div className="actions">
                      <button
                        disabled={busy}
                        onClick={() =>
                          edit(
                            "Assess population reliability",
                            "population.assess",
                            [
                              linked(
                                "population_id",
                                "Population version",
                                e.populations,
                              ),
                              select("status", "Reliability decision", [
                                "RECEIVED",
                                "PROVISIONAL",
                                "UNDER_RELIABILITY_EVALUATION",
                                "READY_FOR_PURPOSE",
                                "DISPUTED",
                              ]),
                              f("purpose", "Intended use"),
                              f(
                                "rationale",
                                "Evidence and rationale",
                                "textarea",
                              ),
                              f(
                                "observable_artifact_ids",
                                "Available source artifact IDs",
                                "textarea",
                              ),
                            ],
                          )
                        }
                      >
                        Assess reliability
                      </button>
                      <button
                        disabled={busy}
                        onClick={() =>
                          edit("Export population", "population.export", [
                            linked(
                              "population_id",
                              "Population version",
                              e.populations,
                            ),
                          ])
                        }
                      >
                        Export population
                      </button>
                      <button
                        disabled={busy}
                        onClick={() =>
                          edit("Export selected IDs", "selection.export", [
                            linked("selection_id", "Selection", e.selections),
                          ])
                        }
                      >
                        Export selected IDs
                      </button>
                    </div>
                    <Table
                      memoryKey="populations"
                      rows={e.populations}
                      onOpen={(r, sequence) =>
                        setDetail({ row: r, kind: "population", sequence })
                      }
                      columns={[
                        { key: "id", label: "Population" },
                        { key: "title", label: "Purpose / unit" },
                        { key: "count", label: "Supplied records" },
                        { key: "version", label: "Version" },
                        {
                          key: "parent_selection_id",
                          label: "Parent selection",
                        },
                        { key: "status", label: "Reliability disposition" },
                        {
                          key: "artifact_id",
                          label: "Original",
                          render: download,
                        },
                      ]}
                    />
                    <SelectionImport
                      engagement={e}
                      onSaved={(updated) => {
                        if (
                          renderEpoch === navigationEpoch.current &&
                          currentEngagement.current === updated.id
                        )
                          setEngagement((previous) =>
                            previous &&
                            previous.id === updated.id &&
                            previous.revision <= updated.revision
                              ? updated
                              : previous,
                          );
                      }}
                    />
                    <SampleResponses
                      engagement={e}
                      busy={busy}
                      onCommand={run}
                    />
                    <h2>Selection history</h2>
                    <Table
                      memoryKey="selections"
                      rows={e.selections}
                      onOpen={(r, sequence) =>
                        setDetail({ row: r, kind: "selection", sequence })
                      }
                      columns={[
                        { key: "id", label: "Selection" },
                        { key: "population_id", label: "Population" },
                        { key: "method", label: "Method" },
                        { key: "selected_ids", label: "Selected IDs" },
                        { key: "purpose", label: "Purpose" },
                        { key: "parent_selection_id", label: "Parent" },
                      ]}
                    />
                    <p className="notice">
                      A supplied population may be incomplete. Reliability work,
                      targeted selections and statistical sampling remain
                      distinct. Later selections preserve their predecessors.
                    </p>
                  </>
                )}
                {section === "notes" && (
                  <>
                    <div className="actions">
                      <label className="search">
                        Search central notes
                        <input
                          type="search"
                          value={query}
                          onChange={(event) => setQuery(event.target.value)}
                          placeholder="Control, participant or phrase"
                        />
                      </label>
                      <button
                        onClick={() =>
                          edit("Add a learner observation", "note.create", [
                            linked("control_id", "Control", e.controls),
                            f("title", "Subject"),
                            f("text", "Observation", "textarea"),
                            f(
                              "source_message_id",
                              "Source message ID",
                              "text",
                              false,
                            ),
                          ])
                        }
                      >
                        Add observation
                      </button>
                    </div>
                    <div className="notes-list">
                      {e.notes
                        .filter((n) =>
                          JSON.stringify(n)
                            .toLowerCase()
                            .includes(query.toLowerCase()),
                        )
                        .map((n) => (
                          <article key={n.id}>
                            <header>
                              <div>
                                <p className="eyebrow">
                                  {controlLink(n)} ·{" "}
                                  {str(n.recorded_at ?? n.simulated_at)}
                                </p>
                                <h2>{str(n.title ?? n.subject ?? n.id)}</h2>
                              </div>
                              <Badge>
                                {human(
                                  n.classification ??
                                    n.claim_type ??
                                    "proposed_note",
                                )}
                              </Badge>
                            </header>
                            <p>{str(n.text ?? n.content)}</p>
                            <NoteProvenance note={n} engagement={e} />
                            {!n.text && Array.isArray(n.bullets) && (
                              <ul>
                                {n.bullets.map((b, i) => (
                                  <li key={i}>{str(b)}</li>
                                ))}
                              </ul>
                            )}
                            {Array.isArray(n.history) &&
                              n.history.length > 0 && (
                                <details>
                                  <summary>
                                    Prior note versions and corrections
                                  </summary>
                                  {(n.history as Row[]).map((prior, index) => (
                                    <article key={index}>
                                      <p>{str(prior.text ?? prior.content)}</p>
                                      <small>
                                        {str(prior.rationale)} ·{" "}
                                        {str(prior.recorded_at)} ·{" "}
                                        {str(prior.actor)}
                                      </small>
                                    </article>
                                  ))}
                                </details>
                              )}
                            <footer>
                              <span>
                                Transcript reference:{" "}
                                {str(
                                  n.source_message_id ??
                                    n.source_message_ids ??
                                    (Array.isArray(n.source_refs)
                                      ? (n.source_refs as Row[]).map(
                                          (ref) => ref.message_id,
                                        )
                                      : undefined),
                                )}
                              </span>
                              <button
                                onClick={() =>
                                  edit(
                                    "Correct note",
                                    "note.correct",
                                    [
                                      f("text", "Corrected text", "textarea"),
                                      f(
                                        "rationale",
                                        "Reason for correction",
                                        "textarea",
                                      ),
                                    ],
                                    {
                                      note_id: n.id,
                                      text: n.text ?? n.content,
                                    },
                                  )
                                }
                              >
                                Correct with history
                              </button>
                            </footer>
                          </article>
                        ))}
                    </div>
                    {!e.notes.length && (
                      <Empty title="Meeting notes will collect here">
                        Each generated note retains its speaker and transcript
                        references. You can add observations without changing
                        company facts.
                      </Empty>
                    )}
                  </>
                )}
                {section === "calendar" && (
                  <>
                    <div className="clock-panel">
                      <div>
                        <p className="eyebrow">Simulated time</p>
                        <h2>
                          {new Intl.DateTimeFormat(undefined, {
                            dateStyle: "full",
                            timeStyle: "short",
                            timeZone: str(e.scope.timezone ?? "UTC"),
                          }).format(new Date(str(e.simulated_at)))}
                        </h2>
                        <p>
                          Engagement timezone: {str(e.scope.timezone ?? "UTC")}
                        </p>
                        <p>
                          Advancement processes scheduled events. Real login
                          expiry is unaffected.
                        </p>
                      </div>
                      <div className="actions">
                        <button
                          onClick={() =>
                            run("clock.advance", { mode: "next_event" })
                          }
                          disabled={busy}
                        >
                          Next event
                        </button>
                        <button
                          onClick={() =>
                            run("clock.advance", { mode: "business_day" })
                          }
                          disabled={busy}
                        >
                          One business day
                        </button>
                        <button
                          onClick={() =>
                            edit(
                              "Advance to a date",
                              "clock.advance",
                              [f("target", "Target date", "date")],
                              { mode: "date" },
                              "Every eligible intervening event is processed in order.",
                            )
                          }
                        >
                          Go to date
                        </button>
                      </div>
                    </div>
                    <Timeline rows={e.calendar} current={e.simulated_at} />
                    <h2>Recorded activity</h2>
                    <Table
                      memoryKey="events"
                      rows={e.events}
                      columns={[
                        { key: "id", label: "Event" },
                        { key: "kind", label: "Activity" },
                        { key: "simulated_at", label: "In-world date" },
                        { key: "recorded_at", label: "Recorded at" },
                        { key: "actor_id", label: "Actor" },
                        { key: "summary", label: "Record" },
                      ]}
                    />
                  </>
                )}
                {section === "findings" && (
                  <>
                    <div className="actions">
                      <button
                        className="primary"
                        onClick={() =>
                          edit(
                            "Record observation or finding",
                            "finding.create",
                            [
                              f("title", "Condition observed"),
                              linked("control_id", "Control", e.controls),
                              select("classification", "Record type", [
                                "observation",
                                "exception",
                                "finding",
                                "evidence_limitation",
                              ]),
                              f(
                                "criterion",
                                "Criterion / objective",
                                "textarea",
                              ),
                              f("evidence_ids", "Supporting evidence IDs"),
                              f(
                                "condition",
                                "Facts, limitations and effect",
                                "textarea",
                              ),
                            ],
                          )
                        }
                      >
                        Record issue +
                      </button>
                    </div>
                    <Table
                      memoryKey="findings"
                      rows={e.findings}
                      onOpen={(r, sequence) =>
                        setDetail({ row: r, kind: "finding", sequence })
                      }
                      columns={[
                        { key: "id", label: "Issue" },
                        { key: "title", label: "Condition" },
                        {
                          key: "control_id",
                          label: "Control",
                          render: controlLink,
                        },
                        { key: "classification", label: "Type" },
                        { key: "status", label: "Disposition" },
                        { key: "due_at", label: "Remediation due" },
                        { key: "original_result", label: "Original result" },
                      ]}
                    />
                    <p className="notice">
                      A later correction or passing retest preserves the
                      original condition and period. Missing evidence does not
                      itself prove fraud or a design failure.
                    </p>
                  </>
                )}
                <RetainedPanel
                  key={sourceContext + ":bound-key"}
                  active={section === "review"}
                >
                  {e.permissions?.includes("instruct") &&
                    bootstrap.capabilities.bound_instructor_keys && (
                      <BoundInstructorKey
                        engagement={e}
                        viewerId={bootstrap.viewer.id}
                        onPreview={(artifact) => {
                          if (!e.permissions?.includes("instruct")) return;
                          const ref = {
                            id: artifact.id,
                            collection: "artifacts",
                            sha256: artifact.sha256,
                            version: artifact.version,
                          };
                          const target = lineageReference(e, ref);
                          if (target)
                            setDetail({
                              kind: "artifact",
                              row: target.row,
                              pinnedReference: ref,
                              returnToBoundSource: true,
                            });
                        }}
                      />
                    )}
                </RetainedPanel>
                {section === "review" && (
                  <>
                    {e.permissions?.includes("instruct") &&
                      supports(
                        bootstrap.capabilities,
                        "instructor_reference_library",
                      ) && (
                        <InstructorKey
                          key={bootstrap.viewer.id + ":" + e.id}
                          engagement={e}
                        />
                      )}
                    <div className="review-intro">
                      <div>
                        <p className="eyebrow">
                          Portable, version-bound review
                        </p>
                        <h2>Your work belongs with its evidence.</h2>
                        <p>
                          Keep firm-native files and their versions. Export a
                          complete offline package for a human reviewer.
                        </p>
                        <div className="actions">
                          <button
                            className="primary"
                            disabled={busy}
                            onClick={() =>
                              run("review.export", { edition: "learner" })
                            }
                          >
                            Export for human review
                          </button>
                          {bootstrap.viewer.roles.some((r) =>
                            [
                              "trainer",
                              "reviewer",
                              "instructor",
                              "admin",
                            ].includes(r.toLowerCase()),
                          ) && (
                            <button
                              disabled={busy}
                              onClick={() =>
                                run("review.export", { edition: "reviewer" })
                              }
                            >
                              Private reviewer edition
                            </button>
                          )}
                        </div>
                      </div>
                      <aside>
                        <h3>Experimental AI review</h3>
                        <p>
                          Suggestions may be wrong. Source support and
                          professional judgment remain separate.
                        </p>
                        <button
                          disabled={!e.capabilities.experimental_review || busy}
                          onClick={() => setExperimentalConsent(true)}
                        >
                          Review experimental disclosure
                        </button>
                        {!e.capabilities.experimental_review && (
                          <small>
                            A model provider is not configured. Human review
                            remains available.
                          </small>
                        )}
                      </aside>
                    </div>
                    <div className="actions">
                      <button
                        onClick={() =>
                          edit(
                            "Assemble a workpaper",
                            "workpaper.add",
                            workpaperFields(e),
                          )
                        }
                      >
                        New structured workpaper
                      </button>
                      <button
                        onClick={() =>
                          edit(
                            "Post-scenario feedback",
                            "survey.submit",
                            [
                              select("realism", "Realism", [
                                "1",
                                "2",
                                "3",
                                "4",
                                "5",
                              ]),
                              select("clarity", "Clarity", [
                                "1",
                                "2",
                                "3",
                                "4",
                                "5",
                              ]),
                              select("usability", "Usability", [
                                "1",
                                "2",
                                "3",
                                "4",
                                "5",
                              ]),
                              {
                                ...select(
                                  "evidence_quality",
                                  "Evidence quality",
                                  ["1", "2", "3", "4", "5"],
                                ),
                                required: false,
                              },
                              {
                                ...select(
                                  "persona_consistency",
                                  "Company response consistency",
                                  ["1", "2", "3", "4", "5"],
                                ),
                                required: false,
                              },
                              {
                                ...select(
                                  "feedback_usefulness",
                                  "Review feedback usefulness",
                                  ["1", "2", "3", "4", "5"],
                                ),
                                required: false,
                              },
                              select("challenge", "Challenge", [
                                "too_low",
                                "appropriate",
                                "too_high",
                              ]),
                              f(
                                "defect_reference",
                                "Affected control / request",
                                "text",
                                false,
                              ),
                              f("feedback", "Feedback and defects", "textarea"),
                            ],
                            undefined,
                            "Feedback stays with this private engagement; it is not automatically sent or used for model training.",
                          )
                        }
                      >
                        Complete feedback survey
                      </button>
                    </div>
                    <Table
                      memoryKey="workpapers"
                      rows={e.workpapers.map((paper) => ({
                        ...paper,
                        ...workpaperVersions(paper).at(-1),
                        id: paper.id,
                        versions: paper.versions,
                      }))}
                      onOpen={(r, sequence) =>
                        setDetail({ row: r, kind: "workpaper", sequence })
                      }
                      columns={[
                        { key: "id", label: "Workpaper" },
                        { key: "title", label: "Title" },
                        { key: "section", label: "Section" },
                        { key: "version", label: "Version" },
                        { key: "status", label: "Assembly status" },
                        {
                          key: "artifact_id",
                          label: "Original",
                          render: (r) =>
                            r.artifact_id ? download(r) : "Structured record",
                        },
                      ]}
                    />
                    <UploadControls
                      kind={uploadKind}
                      setKind={setUploadKind}
                      link={uploadLink}
                      setLink={setUploadLink}
                      requests={e.requests}
                      inputRef={uploadRef}
                      busy={busy}
                      onFile={upload}
                    />
                    <h2>Review and correction history</h2>
                    <Table
                      memoryKey="reviews"
                      rows={e.reviews}
                      onOpen={(r, sequence) =>
                        setDetail({ row: r, kind: "review", sequence })
                      }
                      columns={[
                        { key: "id", label: "Review" },
                        { key: "kind", label: "Review type" },
                        { key: "status", label: "Disposition" },
                        {
                          key: "comment",
                          label: "Observation",
                          render: (r) =>
                            str(
                              r.comment ?? (r.result as Row)?.text ?? r.claim,
                            ),
                        },
                        { key: "workpaper_version", label: "Reviewed version" },
                        { key: "evidence_ids", label: "Supporting references" },
                        { key: "experimental", label: "Experimental" },
                      ]}
                    />
                    <h2>Available exports</h2>
                    <Table
                      memoryKey="exports"
                      rows={e.artifacts.filter((a) => a.kind === "export")}
                      columns={[
                        { key: "name", label: "Package" },
                        { key: "edition", label: "Audience" },
                        { key: "created_at", label: "Created" },
                        { key: "id", label: "Download", render: download },
                      ]}
                    />
                  </>
                )}
                <footer className="workspace-footer">
                  <span>
                    {e.id} · revision {e.revision}
                  </span>
                  <span>
                    Training work product · No professional opinion issued
                  </span>
                </footer>
              </main>
            )}
          </div>
        </div>
        {action && (
          <ActionForm
            key={
              actionDraft
                ? JSON.stringify([actionDraft.key, actionDraft.remote])
                : action.kind + action.title
            }
            draft={actionDraft}
            support={
              e && ["workpaper.add", "workpaper.update"].includes(action.kind)
                ? (values, onChange, editable) => (
                    <>
                      {evidenceHandoff && (
                        <aside className="evidence-context">
                          <p>
                            Your existing personal draft is retained. Add the
                            selected original only after reviewing the restored
                            draft.
                          </p>
                          <p>Selected original: {evidenceHandoff.artifactId}</p>
                          <button
                            type="button"
                            disabled={
                              !editable ||
                              busy ||
                              evidenceHandoff.key !==
                                evidenceContextKey(
                                  e,
                                  bootstrap.viewer.id,
                                  evidenceHandoff.artifactId,
                                ) ||
                              !recordedEvidenceContext(
                                e,
                                evidenceHandoff.artifactId,
                              )?.canDraft
                            }
                            onClick={() => {
                              if (
                                editable &&
                                !busy &&
                                evidenceHandoff.key ===
                                  evidenceContextKey(
                                    e,
                                    bootstrap.viewer.id,
                                    evidenceHandoff.artifactId,
                                  ) &&
                                recordedEvidenceContext(
                                  e,
                                  evidenceHandoff.artifactId,
                                )?.canDraft
                              )
                                onChange({
                                  ...values,
                                  evidence_ids: appendEvidenceReference(
                                    values.evidence_ids,
                                    evidenceHandoff.artifactId,
                                  ).join(", "),
                                });
                            }}
                          >
                            Add this original to draft
                          </button>
                          {evidenceHandoff.key !==
                            evidenceContextKey(
                              e,
                              bootstrap.viewer.id,
                              evidenceHandoff.artifactId,
                            ) && (
                            <p role="status">
                              Source context changed. Reopen the current
                              original before linking it.
                            </p>
                          )}
                        </aside>
                      )}
                      <WorkpaperSupport
                        engagement={e}
                        viewerId={bootstrap.viewer.id}
                        values={values}
                        onTaskIds={
                          editable &&
                          supports(
                            bootstrap.capabilities,
                            "workpaper_procedure_links",
                          )
                            ? (ids) => onChange({ ...values, task_ids: ids })
                            : undefined
                        }
                        onAppendEvidence={
                          editable
                            ? (id) =>
                                onChange({
                                  ...values,
                                  evidence_ids: appendEvidenceReference(
                                    values.evidence_ids,
                                    id,
                                  ).join(", "),
                                })
                            : undefined
                        }
                      />
                    </>
                  )
                : undefined
            }
            onDraftCleanupFailure={() =>
              setNotice(
                "Formal record saved. Personal draft cleanup failed; the saved draft remains and must be reviewed before reuse.",
              )
            }
            action={action}
            busy={busy}
            onClose={() => {
              setAction(null);
              if (evidenceHandoff && e) {
                const artifact = e.artifacts.find(
                  (row) =>
                    row.id === evidenceHandoff.artifactId &&
                    row.status === "AVAILABLE",
                );
                if (
                  artifact &&
                  evidenceHandoff.key ===
                    evidenceContextKey(e, bootstrap.viewer.id, artifact.id)
                )
                  setDetail({ ...evidenceHandoff.detail, row: artifact });
                else
                  setNotice(
                    "Draft retained. The original source context changed; reopen it from current records.",
                  );
              }
              setEvidenceHandoff(null);
            }}
            onSubmit={async (payload, afterFormalSave) => {
              try {
                const saved = await act(
                  action.kind,
                  compatibleWorkpaperValues(
                    action.kind,
                    payload,
                    bootstrap.capabilities,
                  ),
                  afterFormalSave,
                );
                if (
                  saved &&
                  actionDraft &&
                  renderEpoch === navigationEpoch.current
                )
                  actionDraft.store.discardObject(actionDraft.key);
                if (saved) setEvidenceHandoff(null);
                return Boolean(saved);
              } catch {
                return false;
              }
            }}
          />
        )}
        {detail && e && (
          <Detail
            row={detail.row}
            title={str(detail.row.title ?? detail.row.name ?? detail.row.id)}
            onClose={() => setDetail(null)}
          >
            {detail.returnToBoundSource && (
              <button type="button" onClick={() => setDetail(null)}>
                Back to bound source
              </button>
            )}
            {detail.returnTo && (
              <button
                type="button"
                onClick={() => {
                  const back = detail.returnTo!;
                  const collections: Record<string, string> = {
                    population: "populations",
                    selection: "selections",
                    artifact: "artifacts",
                    workpaper: "workpapers",
                  };
                  const ref = {
                    id: back.row.id,
                    collection: collections[back.kind],
                    ...(back.row.version !== undefined
                      ? { version: back.row.version }
                      : {}),
                    ...(back.row.sha256 ? { sha256: back.row.sha256 } : {}),
                  };
                  const target = lineageReference(e, ref);
                  if (target) setDetail({ ...back, row: target.row });
                  else
                    setError(
                      "The original inspection context is no longer available at its pinned version.",
                    );
                }}
              >
                Back to {detail.returnTo.kind} {detail.returnTo.row.id}
              </button>
            )}
            {["population", "selection"].includes(detail.kind) && (
              <PopulationLineage
                engagement={e}
                kind={detail.kind}
                row={detail.row}
                onOpen={(ref) => {
                  const target = lineageReference(e, ref);
                  if (target)
                    setDetail({
                      row: target.row,
                      kind: target.kind,
                      returnTo: detail,
                      pinnedReference: ref,
                      ...(ref.collection === "workpapers" &&
                      typeof ref.version === "number"
                        ? { focusVersion: ref.version }
                        : {}),
                    });
                }}
              />
            )}
            {neighbors && (
              <nav className="actions" aria-label="Inspect filtered records">
                <button
                  disabled={!neighbors.previous}
                  onClick={() => {
                    if (neighbors.previous)
                      setDetail({ ...detail, row: neighbors.previous });
                  }}
                >
                  Previous record
                </button>
                <span>
                  Filtered list · {neighbors.position} of {neighbors.total}
                </span>
                <button
                  disabled={!neighbors.next}
                  onClick={() => {
                    if (neighbors.next)
                      setDetail({ ...detail, row: neighbors.next });
                  }}
                >
                  Next record
                </button>
              </nav>
            )}
            <div className="actions">
              {detail.kind === "workpaper" && (
                <section>
                  {detail.focusVersion !== undefined && (
                    <p>
                      Showing explicitly linked workpaper version{" "}
                      {detail.focusVersion}. Other versions are not substituted.
                    </p>
                  )}
                  <p>
                    Each saved revision is retained with its preparer and
                    timestamps. Reviews identify the exact version reviewed.
                  </p>
                  {e.permissions?.some(
                    (p) => p === "learn" || p === "instruct",
                  ) && (
                    <button
                      disabled={busy}
                      onClick={() => {
                        const paper = detail.row;
                        setDetail(null);
                        edit(
                          "Save a new workpaper version",
                          "workpaper.update",
                          [
                            f("section", "Section", "text", false),
                            f("objective", "Objective", "textarea"),
                            f(
                              "procedures",
                              "Nature, timing and extent",
                              "textarea",
                            ),
                            f(
                              "text",
                              "Work performed and explanation",
                              "textarea",
                              false,
                            ),
                            f(
                              "artifact_id",
                              "Retained original artifact ID",
                              "text",
                              false,
                            ),
                            f(
                              "evidence_ids",
                              "Evidence references",
                              "text",
                              false,
                            ),
                            f(
                              "conclusion",
                              "Conclusion and limitations",
                              "textarea",
                            ),
                          ],
                          newWorkpaperVersion(paper),
                          "This creates a successor revision. Earlier versions and reviews remain available.",
                        );
                      }}
                    >
                      Save new version
                    </button>
                  )}
                  <Table
                    memoryKey={
                      "versions:" +
                      detail.row.id +
                      (detail.focusVersion === undefined
                        ? ""
                        : ":pinned:" + detail.focusVersion)
                    }
                    rows={workpaperVersions(detail.row).filter(
                      (version) =>
                        detail.focusVersion === undefined ||
                        version.version === detail.focusVersion,
                    )}
                    columns={[
                      { key: "version", label: "Version" },
                      { key: "actor", label: "Prepared by" },
                      { key: "recorded_at", label: "Recorded at" },
                      { key: "objective", label: "Objective" },
                      { key: "procedures", label: "Procedures" },
                      { key: "text", label: "Work performed" },
                      {
                        key: "artifact_id",
                        label: "Original",
                        render: (version) =>
                          version.artifact_id
                            ? download(version)
                            : "Structured record",
                      },
                      { key: "evidence_ids", label: "Evidence references" },
                      {
                        key: "task_ids",
                        label: "Explicit procedure references",
                      },
                      { key: "conclusion", label: "Conclusion" },
                      {
                        key: "id",
                        label: "Independent review",
                        render: (version) =>
                          canReviewWorkpaper(
                            detail.row,
                            bootstrap?.viewer.id,
                            e.permissions,
                            version,
                          ) ? (
                            <button
                              disabled={busy}
                              onClick={() => {
                                const paper = detail.row;
                                setDetail(null);
                                edit(
                                  `Review workpaper version ${version.version}`,
                                  "review.comment",
                                  [
                                    f(
                                      "comment",
                                      "Independent review comment",
                                      "textarea",
                                    ),
                                  ],
                                  {
                                    workpaper_id: paper.id,
                                    workpaper_version: version.version,
                                  },
                                  "Your comment is pinned to this exact retained version. It does not replace the preparer's conclusion.",
                                );
                              }}
                            >
                              Review version {str(version.version)}
                            </button>
                          ) : (
                            "Independent reviewer required"
                          ),
                      },
                    ]}
                  />
                </section>
              )}
              {detail.kind === "control" && (
                <>
                  <button
                    onClick={() => {
                      setDetail(null);
                      navigate("pbc");
                    }}
                  >
                    Evidence requests
                  </button>
                  <button
                    onClick={() => {
                      setDetail(null);
                      navigate("meetings");
                    }}
                  >
                    Meet the owner
                  </button>
                  <button
                    onClick={() => {
                      setDetail(null);
                      navigate("notes");
                    }}
                  >
                    Linked notes
                  </button>
                </>
              )}
              {detail.kind === "person" && (
                <button
                  onClick={() => {
                    const person = detail.row;
                    setDetail(null);
                    edit(
                      "Meet this owner",
                      "meeting.create",
                      [
                        f("title", "Meeting subject"),
                        linked("control_id", "Control", e.controls),
                        f("purpose", "Topics", "textarea"),
                      ],
                      { person_id: person.id, mode: "immediate" },
                    );
                  }}
                >
                  Request meeting
                </button>
              )}
              {detail.kind === "request" && (
                <>
                  <button
                    disabled={busy || detail.row.status !== "DRAFT"}
                    onClick={() => {
                      const requestID = detail.row.id;
                      setDetail(null);
                      run("pbc.issue", { request_id: requestID });
                    }}
                  >
                    Issue initial request
                  </button>
                  <button
                    onClick={() => {
                      const r = detail.row;
                      setDetail(null);
                      edit(
                        "Follow up on evidence",
                        "pbc.followup",
                        [
                          f(
                            "message",
                            "Clarification or additional support",
                            "textarea",
                          ),
                          f("due_at", "Revised due date", "date"),
                        ],
                        { request_id: r.id },
                      );
                    }}
                  >
                    Request follow-up
                  </button>
                  <button
                    onClick={() => {
                      const r = detail.row;
                      setDetail(null);
                      edit(
                        "Update request disposition",
                        "pbc.update",
                        [
                          select("status", "Request status", [
                            "CLARIFICATION",
                            "ACCEPTED_FOR_PURPOSE",
                            "WITHDRAWN",
                            "CLOSED",
                          ]),
                          f(
                            "rationale",
                            "Purpose-specific rationale",
                            "textarea",
                          ),
                        ],
                        { request_id: r.id },
                      );
                    }}
                  >
                    Update request status
                  </button>
                </>
              )}
              {detail.kind === "finding" && (
                <>
                  <button
                    onClick={() => {
                      const finding = detail.row;
                      setDetail(null);
                      edit(
                        "Record prospective remediation retest",
                        "remediation.retest",
                        [
                          linked(
                            "remediation_id",
                            "Recorded remediation",
                            (finding.remediations ?? []) as Row[],
                          ),
                          f("test_date", "Test performed on", "date"),
                          f("period_start", "Retest coverage starts", "date"),
                          f("period_end", "Retest coverage ends", "date"),
                          f(
                            "procedures",
                            "Procedures actually performed",
                            "textarea",
                          ),
                          f(
                            "rationale",
                            "Evidence and limitations",
                            "textarea",
                          ),
                          f(
                            "evidence_ids",
                            "Available supporting artifact IDs",
                            "textarea",
                          ),
                          select("result", "Prospective retest disposition", [
                            "SUPPORTED_FOR_RETEST_PERIOD",
                            "EXCEPTION_REMAINS",
                            "INCONCLUSIVE",
                          ]),
                        ],
                        { finding_id: finding.id },
                        "The original finding and prior-period conclusion remain unchanged. A retest records only the new coverage and work performed.",
                      );
                    }}
                  >
                    Record prospective retest
                  </button>
                  <button
                    onClick={() => {
                      const r = detail.row;
                      setDetail(null);
                      edit(
                        "Record remediation or retest",
                        "remediation.record",
                        [
                          select("status", "Remediation state", [
                            "proposed",
                            "in_progress",
                            "implemented",
                            "awaiting_validation",
                            "validated_prospectively",
                            "ineffective",
                          ]),
                          f("action", "Action / retest performed", "textarea"),
                          f("due_at", "Due date", "date"),
                          f("evidence_ids", "New supporting evidence"),
                          f("period_start", "Retest coverage starts", "date"),
                          f("period_end", "Retest coverage ends", "date"),
                        ],
                        { finding_id: r.id },
                      );
                    }}
                  >
                    Remediation & retest
                  </button>
                  <button
                    onClick={() => {
                      const r = detail.row;
                      setDetail(null);
                      edit(
                        "Update finding",
                        "finding.update",
                        [
                          select("status", "Disposition", [
                            "open",
                            "disputed",
                            "awaiting_support",
                            "closed_with_limitation",
                            "closed_prospectively",
                          ]),
                          f(
                            "response",
                            "Management response / rationale",
                            "textarea",
                          ),
                        ],
                        { finding_id: r.id },
                      );
                    }}
                  >
                    Record disposition
                  </button>
                </>
              )}
              {detail.kind === "review" &&
                detail.row.kind === "EXPERIMENTAL_AI" && (
                  <section className="experimental">
                    <strong>{str(detail.row.warning)}</strong>
                    <p>{str((detail.row.result as Row)?.text)}</p>
                    {Array.isArray((detail.row.result as Row)?.findings) &&
                      ((detail.row.result as Row).findings as Row[]).map(
                        (finding, index) => (
                          <article key={index}>
                            <Badge>
                              Experimental · {str(finding.category)}
                            </Badge>
                            <h3>{str(finding.claim)}</h3>
                            {Boolean(
                              (finding.learner_excerpt as Row)?.text,
                            ) && (
                              <blockquote>
                                <p>
                                  {str((finding.learner_excerpt as Row).text)}
                                </p>
                                <cite>
                                  {str(
                                    (finding.learner_excerpt as Row).source_ref,
                                  )}
                                </cite>
                              </blockquote>
                            )}
                            <p>Source references: {str(finding.source_refs)}</p>
                            <p>{str(finding.rationale)}</p>
                            <p>Uncertainty: {str(finding.uncertainty)}</p>
                            <p>
                              Suggested follow-up:{" "}
                              {str(finding.suggested_followup)}
                            </p>
                          </article>
                        ),
                      )}
                    {Array.isArray((detail.row.result as Row)?.observations) &&
                      ((detail.row.result as Row).observations as Row[]).map(
                        (o, i) => (
                          <p key={i}>
                            {str(o.text)}{" "}
                            <small>
                              Sources: {str(o.source_refs)} · Limitation:{" "}
                              {str(o.limitation)}
                            </small>
                          </p>
                        ),
                      )}
                  </section>
                )}
              {detail.kind === "review" && (
                <button
                  onClick={() => {
                    const r = detail.row;
                    setDetail(null);
                    edit(
                      "Respond to review",
                      "review.resolve",
                      [
                        select("disposition", "Your response", [
                          "agree",
                          "disagree",
                          "correct",
                          "missing_context",
                          "human_review",
                        ]),
                        f("response", "Correction and evidence", "textarea"),
                      ],
                      { review_id: r.id },
                    );
                  }}
                >
                  Agree, correct or appeal
                </button>
              )}
              {detail.kind === "artifact" && (
                <>
                  {download(detail.row)}
                  <EvidenceContext
                    engagement={e}
                    artifactId={detail.row.id}
                    viewerId={bootstrap.viewer.id}
                    onOpen={(ref) => {
                      const target = lineageReference(e, { ...ref });
                      if (target)
                        setDetail({
                          row: target.row,
                          kind: target.kind,
                          returnTo: detail,
                          pinnedReference: { ...ref },
                          ...(ref.version !== undefined
                            ? { focusVersion: ref.version }
                            : {}),
                        });
                    }}
                    onStartDraft={
                      !busy
                        ? (selection) => {
                            const context = recordedEvidenceContext(
                              e,
                              selection.artifactId,
                            );
                            if (!context?.canDraft) return;
                            const handoff = {
                              key: evidenceContextKey(
                                e,
                                bootstrap.viewer.id,
                                selection.artifactId,
                              ),
                              artifactId: selection.artifactId,
                              detail,
                            };
                            setDetail(null);
                            edit(
                              "Assemble a workpaper",
                              "workpaper.add",
                              workpaperFields(e),
                              undefined,
                              "Your personal draft is restored first. Add the selected original explicitly; no conclusion is supplied.",
                            );
                            setEvidenceHandoff(handoff);
                          }
                        : undefined
                    }
                  />
                </>
              )}
              {detail.kind === "population" && (
                <button
                  onClick={() => {
                    const r = detail.row;
                    setDetail(null);
                    edit(
                      "Select from this population",
                      "population.select",
                      [
                        select("method", "Method", [
                          "manual",
                          "simple_random",
                          "systematic",
                          "entire_population",
                        ]),
                        f(
                          "selected_ids",
                          "Selected IDs, one per line",
                          "textarea",
                          false,
                        ),
                        f("size", "Sample size", "number", false),
                        f("purpose", "Purpose and rationale", "textarea"),
                      ],
                      { population_id: r.id },
                    );
                  }}
                >
                  Create linked selection
                </button>
              )}
            </div>
          </Detail>
        )}
        {experimentalConsent && e && (
          <ReviewDialog
            engagement={e}
            bootstrap={bootstrap}
            busy={busy}
            onCommand={act}
            onClose={() => setExperimentalConsent(false)}
          />
        )}
      </div>
    </TableWorkspace>
  );
}
function UploadControls({
  kind,
  setKind,
  link,
  setLink,
  requests,
  inputRef,
  busy,
  onFile,
}: {
  kind: string;
  setKind: (s: string) => void;
  link: string;
  setLink: (s: string) => void;
  requests: Row[];
  inputRef: React.RefObject<HTMLInputElement | null>;
  busy: boolean;
  onFile: (file: File) => Promise<void>;
}) {
  return (
    <section className="upload-bar">
      <label>
        File purpose
        <select
          value={kind}
          onChange={(e) => {
            setKind(e.target.value);
            setLink("");
          }}
        >
          <option value="workpaper">Learner workpaper</option>
          <option value="evidence">Supplied evidence for PBC</option>
        </select>
      </label>
      <label>
        Link to request (required for supplied evidence)
        <select
          disabled={kind === "workpaper"}
          value={link}
          onChange={(e) => setLink(e.target.value)}
        >
          <option value="">Engagement-level file</option>
          {requests.map((r) => (
            <option key={r.id} value={r.id}>
              {r.id} · {str(r.title)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Retain original file
        <input
          ref={inputRef}
          type="file"
          disabled={busy || (kind === "evidence" && !link)}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void onFile(file);
          }}
        />
      </label>
      <p>
        Native files remain unchanged. Active content is not executed;
        unsupported previews retain the original.
      </p>
    </section>
  );
}
function Timeline({ rows, current }: { rows: Row[]; current: string }) {
  const date = new Date(current);
  const valid = !Number.isNaN(date.valueOf());
  const year = valid ? date.getUTCFullYear() : 2026,
    month = valid ? date.getUTCMonth() : 0;
  const days = new Date(Date.UTC(year, month + 1, 0)).getUTCDate(),
    offset = new Date(Date.UTC(year, month, 1)).getUTCDay();
  return (
    <>
      <div className="calendar-grid" aria-label="Engagement calendar">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <strong key={d}>{d}</strong>
        ))}
        {Array.from({ length: offset }, (_, i) => (
          <div className="outside" key={`blank${i}`} />
        ))}
        {Array.from({ length: days }, (_, i) => {
          const key = `${year}-${String(month + 1).padStart(2, "0")}-${String(i + 1).padStart(2, "0")}`;
          return (
            <div key={key} className={current.startsWith(key) ? "today" : ""}>
              <span>{i + 1}</span>
              {rows
                .filter((r) =>
                  str(r.scheduled_at ?? r.due_at ?? r.simulated_at).startsWith(
                    key,
                  ),
                )
                .map((r) => (
                  <p key={r.id}>{str(r.title ?? r.kind)}</p>
                ))}
            </div>
          );
        })}
      </div>
      <Table
        memoryKey="calendar"
        rows={rows}
        columns={[
          { key: "id", label: "Calendar event" },
          { key: "title", label: "Activity" },
          { key: "scheduled_at", label: "Scheduled" },
          { key: "status", label: "State" },
          { key: "request_id", label: "Linked PBC" },
        ]}
      />
    </>
  );
}
