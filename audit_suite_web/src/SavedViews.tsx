import { DeferredPanel } from "./DeferredPanel";
import { useEffect, useRef, useState } from "react";
import { ApiError, request, type Engagement, type Row } from "./api";
import { useTableMemory } from "./TableWorkspace";
import type { ContextLink } from "./investigationContext";
import {
  currentViewResponse,
  exactReferenceDescriptor,
  referenceSections,
  restoredNavigation,
  savedViewContext,
  savedViewsPath,
  savedViewTables,
  savedViewSectionLabels,
  savedViewTableLabels,
  type SavedView,
  type SavedViewNavigation,
  type SavedViewReferenceDescriptor,
} from "./savedViews";
export type SavedViewsProps = {
  engagement: Engagement;
  viewerId: string;
  enabled: boolean;
  getNavigation: () => Pick<
    SavedViewNavigation,
    "section" | "query" | "framework" | "scroll_top"
  >;
  selectedReference?: SavedViewReferenceDescriptor | null;
  onRestore: (
    navigation: SavedViewNavigation,
    resolvedRow: Row | null,
    opener: HTMLButtonElement,
  ) => void;
};
export function SavedViews(props: SavedViewsProps) {
  if (
    !props.enabled ||
    !props.engagement.permissions?.some((p) =>
      ["learn", "review", "instruct"].includes(p),
    )
  )
    return null;
  return (
    <DeferredPanel context={savedViewContext(props.engagement, props.viewerId)} summary="Personal saved views">
      {() => <SavedViewsPanel key={savedViewContext(props.engagement, props.viewerId)} {...props} />}
    </DeferredPanel>
  );
}
function SavedViewsPanel({
  engagement: e,
  getNavigation,
  selectedReference,
  onRestore,
}: SavedViewsProps) {
  const memory = useTableMemory();
  const [views, setViews] = useState<SavedView[]>([]);
  const [title, setTitle] = useState("");
  const [tableId, setTableId] = useState("");
  const [includeReference, setIncludeReference] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const epoch = useRef(0),
    loadSequence = useRef(0);
  const pending = useRef<{ signature: string; command_id: string } | null>(
    null,
  );
  const latest = useRef({ getNavigation, selectedReference });
  latest.current = { getNavigation, selectedReference };
  const navigationIdentity = () => {
    const nav = latest.current.getNavigation();
    return JSON.stringify([
      nav.section,
      nav.query,
      nav.framework,
      latest.current.selectedReference,
    ]);
  };
  const base = savedViewsPath(e.id);
  const section = getNavigation().section;
  const tables = savedViewTables[section] ?? [];
  const canLink =
    selectedReference && referenceSections[selectedReference.kind] === section;
  async function load() {
    const generation = epoch.current,
      sequence = ++loadSequence.current;
    const response = await request<{ views: SavedView[] }>(base);
    if (generation !== epoch.current || sequence !== loadSequence.current)
      return;
    if (
      !Array.isArray(response.views) ||
      response.views.some((view) => !currentViewResponse(view, e))
    )
      throw new Error(
        "Saved view list no longer matches this workspace. Refresh the engagement.",
      );
    setViews(response.views);
  }
  useEffect(() => {
    epoch.current++;
    const generation = epoch.current;
    void load().catch((err) => {
      if (generation === epoch.current)
        setError(
          err instanceof Error ? err.message : "Saved views unavailable",
        );
    });
    return () => {
      epoch.current++;
      loadSequence.current++;
    };
  }, []);
  function commandId(payload: unknown) {
    const signature = JSON.stringify(payload);
    if (pending.current?.signature !== signature)
      pending.current = { signature, command_id: crypto.randomUUID() };
    return pending.current.command_id;
  }
  async function run(action: (current: () => boolean) => Promise<void>) {
    const generation = epoch.current;
    const current = () => generation === epoch.current;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action(current);
    } catch (err) {
      if (current()) {
        setError(err instanceof Error ? err.message : "Saved view unavailable");
        if (err instanceof ApiError && [401, 403, 404].includes(err.status))
          setViews([]);
        if (err instanceof ApiError && err.status === 409)
          void load().catch(() => {});
      }
    } finally {
      if (current()) setBusy(false);
    }
  }
  function save(existing?: SavedView) {
    // Capture actual navigation, scroll and table state at this explicit click.
    const nav = getNavigation();
    const table =
      tableId && savedViewTables[nav.section]?.includes(tableId) && memory
        ? { id: tableId, ...memory.read(tableId) }
        : null;
    const descriptor =
      includeReference &&
      selectedReference &&
      referenceSections[selectedReference.kind] === nav.section
        ? { ...selectedReference }
        : null;
    const selectedTitle = title.trim();
    if (!selectedTitle) {
      setError("Enter a title before saving.");
      return;
    }
    void run(async (current) => {
      let reference: ContextLink | null = null;
      if (descriptor) {
        reference = await request<ContextLink>(
          base + "/link",
          "POST",
          descriptor,
        );
        if (!current()) return;
        if (!exactReferenceDescriptor(reference, descriptor))
          throw new Error(
            "Selected record changed. Reopen the exact version before saving.",
          );
      }
      const payload = {
        payload: {
          section: nav.section,
          query: nav.query,
          framework: nav.framework,
          scroll_top: nav.scroll_top,
          title: selectedTitle,
          table,
          reference,
        },
        expected_engagement_revision: e.revision,
        ...(existing ? { expected_version: existing.version } : {}),
      };
      const id = commandId({ id: existing?.id ?? null, ...payload });
      const saved = await request<SavedView>(
        existing ? base + "/" + encodeURIComponent(existing.id) : base,
        existing ? "PUT" : "POST",
        { ...payload, command_id: id },
      );
      if (!current()) return;
      if (!currentViewResponse(saved, e, existing?.id))
        throw new Error(
          "Save response does not match this workspace. Refresh before retrying.",
        );
      pending.current = null;
      setNotice(
        saved.status === "ACTIVE"
          ? "Personal navigation saved. No audit work was changed."
          : "This view has already been cleared.",
      );
      await load();
    });
  }
  function restore(view: SavedView, opener: HTMLButtonElement) {
    const startingNavigation = navigationIdentity();
    void run(async (current) => {
      const response = await request<SavedView>(
        base + "/" + encodeURIComponent(view.id) + "/restore",
        "POST",
        {
          expected_version: view.version,
          expected_engagement_revision: e.revision,
        },
      );
      if (!current()) return;
      if (navigationIdentity() !== startingNavigation)
        throw new Error(
          "Navigation changed while restore was pending. Restore again when ready.",
        );
      const restored = restoredNavigation(response, e, view.id, view.version);
      if (restored.navigation.table && memory) {
        const { id, ...table } = restored.navigation.table;
        memory.restore(id, table);
      }
      onRestore(restored.navigation, restored.row, opener);
      if (current())
        setNotice(
          "Saved navigation restored. Table pages and scroll may be limited by the current records and viewport.",
        );
    });
  }
  function clear(view: SavedView) {
    void run(async (current) => {
      const payload = {
        expected_version: view.version,
        expected_engagement_revision: e.revision,
      };
      const response = await request<SavedView>(
        base + "/" + encodeURIComponent(view.id) + "/clear",
        "POST",
        { ...payload, command_id: commandId({ clear: view.id, ...payload }) },
      );
      if (!current()) return;
      if (!currentViewResponse(response, e, view.id))
        throw new Error("Clear response does not match this workspace.");
      pending.current = null;
      setNotice("Saved view cleared.");
      await load();
    });
  }
  return (
    <div>
      <p>
        Save your current navigation in this workspace. This stores filters and
        optional exact record links, not document contents or draft work.
      </p>
      <p>
        Section to save:{" "}
        <strong>{savedViewSectionLabels[section] ?? "Workspace"}</strong>
        {canLink && (
          <>
            {" "}
            · Selected record: {selectedReference.id},{" "}
            {selectedReference.version === null
              ? "record pin"
              : `version ${selectedReference.version}`}
          </>
        )}
      </p>
      <label>
        View title{" "}
        <input
          maxLength={120}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          disabled={busy}
        />
      </label>
      {tables.length > 0 && memory && (
        <label>
          Table navigation{" "}
          <select
            value={tables.includes(tableId) ? tableId : ""}
            onChange={(event) => setTableId(event.target.value)}
            disabled={busy}
          >
            <option value="">Do not save a table</option>
            {tables.map((id) => (
              <option key={id} value={id}>
                {savedViewTableLabels[id]}
              </option>
            ))}
          </select>
        </label>
      )}
      {canLink && (
        <label>
          <input
            type="checkbox"
            checked={includeReference}
            onChange={(event) => setIncludeReference(event.target.checked)}
            disabled={busy}
          />
          Include this exact record version
        </label>
      )}
      <button disabled={busy || !title.trim()} onClick={() => save()}>
        Save current view
      </button>
      <button
        disabled={busy}
        onClick={() =>
          void run(async () => {
            await load();
          })
        }
      >
        Refresh saved views
      </button>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      {!views.length && <p>No personal views saved.</p>}
      <ul>
        {views.map((view) => (
          <li key={view.id}>
            <strong>
              {view.personal_content_visible && view.user
                ? view.user.title
                : view.status === "CLEARED"
                  ? "Cleared view"
                  : "View unavailable in the current context"}
            </strong>
            <span>
              {" "}
              · version {view.version} · {view.status.toLowerCase()}
            </span>
            {view.personal_content_visible && view.user && (
              <p>
                {savedViewSectionLabels[view.user.section] ?? "Workspace"}
                {view.user.table &&
                  ` · ${savedViewTableLabels[view.user.table.id]}, page ${view.user.table.page + 1}`}
                {view.user.reference &&
                  ` · ${view.user.reference.id}, ${view.user.reference.version === null ? "record pin" : `version ${view.user.reference.version}`}`}
              </p>
            )}
            {!view.restorable && view.status === "ACTIVE" && (
              <p>
                This view cannot be restored:{" "}
                {view.context_status !== "CURRENT"
                  ? "workspace context changed"
                  : (view.target_status ?? "target unavailable")}
                .
              </p>
            )}
            {view.revision_status === "ENGAGEMENT_ADVANCED" && (
              <p>
                Saved at engagement revision {view.engagement_revision}; checked
                against revision {e.revision}.
              </p>
            )}
            <button
              disabled={busy || !view.restorable}
              onClick={(event) => restore(view, event.currentTarget)}
            >
              Restore view
            </button>
            {view.status === "ACTIVE" && (
              <>
                <button
                  disabled={busy || !title.trim()}
                  onClick={() => save(view)}
                >
                  Replace with current view
                </button>
                <button disabled={busy} onClick={() => clear(view)}>
                  Clear view
                </button>
              </>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
