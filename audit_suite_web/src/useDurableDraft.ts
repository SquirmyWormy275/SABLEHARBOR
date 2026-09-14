import { useEffect, useRef, useState } from "react";
import type { DraftKey } from "./draftContext";
import {
  readDraft,
  writeDraft,
  deleteDraft,
  draftConflict,
  type PersonalDraft,
} from "./durableDraft";
export function useDurableDraft(
  key: DraftKey | undefined,
  onRestore: (draft: PersonalDraft) => void,
) {
  const [ready, setReady] = useState(!key),
    [status, setStatus] = useState("Loading personal draft…"),
    [error, setError] = useState(""),
    [remote, setRemote] = useState<PersonalDraft | null>(null),
    [blocked, setBlocked] = useState(false);
  const version = useRef(0),
    pending = useRef<{
      key: DraftKey;
      values: Record<string, unknown>;
      commandId: string;
    } | null>(null),
    timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined),
    running = useRef<Promise<boolean> | null>(null),
    alive = useRef(true),
    restore = useRef(onRestore),
    guard = useRef(false);
  restore.current = onRestore;
  function fail(message: string) {
    if (alive.current) {
      setError(message);
      setStatus("Draft not saved; your text remains in this form.");
    }
  }
  async function load() {
    if (!key) return;
    setReady(false);
    try {
      const saved = await readDraft(key);
      if (!alive.current) return;
      version.current = saved.version;
      guard.current = saved.status === "STALE";
      setBlocked(guard.current);
      setRemote(guard.current ? saved : null);
      setError("");
      restore.current(saved);
      setStatus(
        saved.status === "DRAFT"
          ? "Personal draft restored."
          : saved.status === "STALE"
            ? "Previous draft scope or access is stale. Discard it explicitly before saving a new draft."
            : "No saved personal draft.",
      );
      setReady(true);
    } catch (e) {
      fail((e as Error).message);
    }
  }
  useEffect(() => {
    alive.current = true;
    void load();
    return () => {
      alive.current = false;
      clearTimeout(timer.current);
    };
  }, []);
  async function flush(): Promise<boolean> {
    clearTimeout(timer.current);
    if (!key) return true;
    if (!ready || guard.current) return false;
    if (running.current) {
      const success = await running.current;
      if (!success) return false;
      return flush();
    }
    if (!pending.current) return true;
    const next = pending.current;
    pending.current = null;
    if (alive.current) setStatus("Saving personal draft…");
    const promise = (async () => {
      try {
        const saved = await writeDraft(
          next.key,
          version.current,
          next.values,
          next.commandId,
        );
        version.current = saved.version;
        if (alive.current) {
          setError("");
          setStatus("Personal draft saved; not submitted as an audit record.");
        }
        return true;
      } catch (e) {
        if (!pending.current) pending.current = next;
        if (draftConflict(e)) {
          guard.current = true;
          if (alive.current) setBlocked(true);
          try {
            const saved = await readDraft(next.key);
            if (alive.current) setRemote(saved);
          } catch {}
        }
        fail(
          draftConflict(e)
            ? "Another session changed this draft. Compare the saved draft before choosing which text to keep."
            : (e as Error).message,
        );
        return false;
      }
    })();
    running.current = promise;
    const ok = await promise;
    running.current = null;
    if (ok && pending.current) return flush();
    return ok;
  }
  function schedule(values: Record<string, unknown>, baseKey = key) {
    if (!baseKey) return;
    pending.current = {
      key: baseKey,
      values: { ...values },
      commandId: crypto.randomUUID(),
    };
    setStatus("Unsaved changes in this form.");
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      void flush();
    }, 600);
  }
  async function discard() {
    if (!key) return true;
    clearTimeout(timer.current);
    if (running.current) await running.current;
    try {
      const result = await deleteDraft(key, remote?.version ?? version.current);
      version.current = result.version;
      pending.current = null;
      guard.current = false;
      if (alive.current) {
        setBlocked(false);
        setRemote(null);
        setError("");
        setStatus("Personal draft discarded.");
      }
      return true;
    } catch (e) {
      fail((e as Error).message);
      if (draftConflict(e)) {
        guard.current = true;
        if (alive.current) setBlocked(true);
        try {
          const saved = await readDraft(key);
          if (alive.current) setRemote(saved);
        } catch {}
      }
      return false;
    }
  }
  function useRemote() {
    if (!remote) return;
    version.current = remote.version;
    pending.current = null;
    guard.current = remote.status === "STALE";
    setBlocked(guard.current);
    restore.current(remote);
    setError("");
    setStatus("Saved personal draft selected.");
    if (!guard.current) setRemote(null);
  }
  function keepLocal() {
    if (!remote || remote.status === "STALE") return;
    version.current = remote.version;
    guard.current = false;
    setBlocked(false);
    setRemote(null);
    setError("");
    void flush();
  }
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (pending.current || running.current) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);
  return {
    ready,
    status,
    error,
    remote,
    blocked,
    schedule,
    flush,
    discard,
    useRemote,
    keepLocal,
    retry: load,
  };
}
