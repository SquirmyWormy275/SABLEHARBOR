import { useEffect, useRef, useState } from "react";
import { ApiError, request, type Engagement } from "./api";
import { sameDebriefValue } from "./instructorDebrief";
import {
  assertSavedKeyView,
  keyViewContext,
  type KeyViewFilters,
  type KeyViewKind,
  type SavedKeyView,
} from "./instructorKeyViews";
export type InstructorKeyViewsProps = {
  engagement: Engagement;
  viewerId: string;
  enabled: boolean;
  kind: KeyViewKind;
  keyPin: string;
  filters: KeyViewFilters;
  validate: (value: KeyViewFilters) => KeyViewFilters;
  onRestore: (value: KeyViewFilters) => void;
};
export function InstructorKeyViews(props: InstructorKeyViewsProps) {
  if (
    !props.enabled ||
    !props.viewerId ||
    !props.engagement.permissions?.includes("instruct")
  )
    return null;
  return (
    <Panel
      key={keyViewContext(
        props.engagement,
        props.viewerId,
        props.kind,
        props.keyPin,
      )}
      {...props}
    />
  );
}
function Panel({
  engagement: e,
  kind,
  keyPin,
  filters,
  validate,
  onRestore,
}: InstructorKeyViewsProps) {
  const base = `/api/engagements/${encodeURIComponent(e.id)}/instructor-key-views`;
  const [views, setViews] = useState<SavedKeyView[]>([]),
    [title, setTitle] = useState(""),
    [editId, setEditId] = useState<string | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [replace, setReplace] = useState(false),
    [retry, setRetry] = useState(false);
  const epoch = useRef(0),
    baseline = useRef(structuredClone(filters)),
    latest = useRef({ filters, validate, onRestore }),
    pending = useRef<{
      path: string;
      body: Record<string, unknown>;
      operation: "save" | "delete";
    } | null>(null);
  latest.current = { filters, validate, onRestore };
  useEffect(() => {
    epoch.current++;
    return () => {
      epoch.current++;
    };
  }, []);
  const dirty =
    !sameDebriefValue(filters, baseline.current) || title.trim() !== "";
  async function load() {
    const n = epoch.current;
    setBusy(true);
    setError("");
    try {
      const v = await request<{
        engagement_id: string;
        current_engagement_revision: number;
        kind: KeyViewKind;
        views: SavedKeyView[];
      }>(base + "?kind=" + kind);
      if (n !== epoch.current) return;
      if (
        v.engagement_id !== e.id ||
        v.current_engagement_revision !== e.revision ||
        v.kind !== kind ||
        !Array.isArray(v.views) ||
        v.views.length > 16
      )
        throw Error("Saved Key views changed. Reload the workspace.");
      const rows = v.views.map((x) => assertSavedKeyView(x, e, kind, keyPin));
      if (rows.some((x) => x.navigation !== null))
        throw Error("Listing must not restore navigation.");
      setViews(rows);
    } catch (err) {
      if (n === epoch.current) {
        setError((err as Error).message);
        setViews([]);
      }
    } finally {
      if (n === epoch.current) setBusy(false);
    }
  }
  async function mutate(operation: "save" | "delete", row?: SavedKeyView) {
    if (busy) return;
    const n = epoch.current;
    setError("");
    let next = pending.current;
    try {
      if (!next) {
        let body: Record<string, unknown>,
          path = base;
        if (operation === "save") {
          const state = latest.current.validate(latest.current.filters);
          if (!title.trim() || title.length > 120)
            throw Error("Name this saved Key view (up to120 characters).");
          const old = views.find((x) => x.id === editId);
          if (editId && !old)
            throw Error("Reload the selected saved view before updating it.");
          body = {
            view_id: editId,
            kind,
            key_pin: keyPin,
            user: { ...state, title },
            expected_version: old?.version ?? 0,
            expected_engagement_revision: e.revision,
            command_id: crypto.randomUUID(),
          };
        } else {
          if (!row) throw Error("Choose a saved Key view.");
          path += `/${encodeURIComponent(row.id)}/delete`;
          body = {
            expected_version: row.version,
            expected_engagement_revision: e.revision,
            command_id: crypto.randomUUID(),
          };
        }
        next = { path, body, operation };
        pending.current = next;
      }
      setBusy(true);
      const value = await request<SavedKeyView>(next.path, "POST", next.body);
      if (n !== epoch.current) return;
      assertSavedKeyView(value, e, kind, keyPin);
      if (
        value.version !== Number(next.body.expected_version) + 1 ||
        (next.body.view_id && value.id !== next.body.view_id) ||
        (next.operation === "delete" &&
          !next.path.endsWith(
            "/" + encodeURIComponent(value.id) + "/delete",
          )) ||
        (next.operation === "save" &&
          !sameDebriefValue(value.user, next.body.user))
      )
        throw Error(
          "Saved Key view receipt does not match the exact requested filters/version.",
        );
      if (
        value.navigation !== null ||
        value.status !== (next.operation === "save" ? "ACTIVE" : "DELETED")
      )
        throw Error(
          "Saved Key view receipt differs from the requested operation.",
        );
      pending.current = null;
      setRetry(false);
      setViews((old) => [
        ...old.filter((x) => x.id !== value.id),
        ...(value.status === "ACTIVE" ? [value] : []),
      ]);
      if (next.operation === "save") {
        setTitle("");
        setEditId(null);
        const saved = next.body.user as KeyViewFilters & { title: string };
        const { title: _, ...nav } = saved;
        baseline.current = nav as KeyViewFilters;
        setNotice("Key view saved. Current filters were not replaced.");
      } else
        setNotice("Saved Key view deleted; current filters are unchanged.");
    } catch (err) {
      if (n !== epoch.current) return;
      setError((err as Error).message);
      if (pending.current) {
        if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
          pending.current = null;
          setRetry(false);
          if ([401, 403].includes(err.status)) setViews([]);
        } else setRetry(true);
      }
    } finally {
      if (n === epoch.current) setBusy(false);
    }
  }
  async function restore(row: SavedKeyView) {
    if (busy || retry || (dirty && !replace)) return;
    const n = epoch.current,
      starting = JSON.stringify(latest.current.filters);
    setBusy(true);
    setError("");
    try {
      const value = await request<SavedKeyView>(
        base + `/${encodeURIComponent(row.id)}/restore`,
        "POST",
        {
          expected_version: row.version,
          expected_engagement_revision: e.revision,
          expected_key_pin: keyPin,
        },
      );
      if (n !== epoch.current) return;
      assertSavedKeyView(value, e, kind, keyPin);
      if (
        value.id !== row.id ||
        value.version !== row.version ||
        !value.navigation ||
        !sameDebriefValue(value.navigation, value.user) ||
        starting !== JSON.stringify(latest.current.filters)
      )
        throw Error(
          "Current filters or saved view changed. Inspect and restore again explicitly.",
        );
      const { title: _, ...nav } = value.navigation;
      const accepted = latest.current.validate(nav as KeyViewFilters);
      latest.current.onRestore(accepted);
      baseline.current = accepted;
      setTitle("");
      setEditId(null);
      setReplace(false);
      setNotice(
        "Exact saved filters restored. No original, comparison or scenario detail was fetched.",
      );
    } catch (err) {
      if (n === epoch.current) {
        setError((err as Error).message);
        if (err instanceof ApiError && [401, 403, 409].includes(err.status))
          setViews([]);
      }
    } finally {
      if (n === epoch.current) setBusy(false);
    }
  }
  return (
    <details className="panel">
      <summary>Saved Key views</summary>
      <p>
        Private to this instructor and exact Key. Saving and restoring changes
        no audit work.
      </p>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <fieldset disabled={busy || retry}>
        <legend>
          Save current {kind === "BOUND" ? "bound-source" : "archive"} filters
        </legend>
        <label>
          Saved Key view name
          <input
            maxLength={120}
            value={title}
            onChange={(ev) => setTitle(ev.target.value)}
          />
        </label>
        <button type="button" onClick={() => void mutate("save")}>
          {editId ? "Save new version of Key view" : "Save current Key view"}
        </button>
        {!editId && title && (
          <button type="button" onClick={() => setTitle("")}>
            Discard unsaved view name
          </button>
        )}
        {editId && (
          <button
            onClick={() => {
              setEditId(null);
              setTitle("");
            }}
          >
            Cancel saved view update
          </button>
        )}
        <button onClick={() => void load()}>Load saved Key views</button>
      </fieldset>
      {retry && (
        <>
          <p>
            The response was not confirmed. Retry preserves the exact original
            command and filters.
          </p>
          <button
            disabled={busy}
            onClick={() => void mutate(pending.current!.operation)}
          >
            Retry exact saved Key view request
          </button>
          <button
            disabled={busy}
            onClick={() => {
              pending.current = null;
              setRetry(false);
              setNotice(
                "Pending request discarded locally. Reload saved views before repeating the operation.",
              );
            }}
          >
            Discard pending saved view request
          </button>
        </>
      )}
      {dirty && (
        <label>
          <input
            type="checkbox"
            checked={replace}
            onChange={(ev) => setReplace(ev.target.checked)}
          />
          Allow explicit restore to replace my current unsaved Key filters and
          name
        </label>
      )}
      {views.map((row) => (
        <article key={row.id}>
          <h4>{row.personal_content_visible ? row.user?.title : row.id}</h4>
          <p>
            {row.context_status} · {row.revision_status}
          </p>
          {row.personal_content_visible && (
            <p>
              Saved revision {row.saved_engagement_revision}; current revision{" "}
              {row.current_engagement_revision}
            </p>
          )}
          <button
            disabled={busy || retry || !row.restorable || (dirty && !replace)}
            onClick={() => void restore(row)}
          >
            Restore Key view {row.id}
          </button>
          {row.personal_content_visible && (
            <button
              disabled={
                busy || retry || (title.trim() !== "" && editId !== row.id)
              }
              onClick={() => {
                setEditId(row.id);
                setTitle(row.user!.title);
                setNotice(
                  "Update will save the current filters; no saved filters were restored.",
                );
              }}
            >
              Update Key view {row.id}
            </button>
          )}
          <button
            disabled={busy || retry}
            onClick={() => void mutate("delete", row)}
          >
            Delete Key view {row.id}
          </button>
        </article>
      ))}
    </details>
  );
}
