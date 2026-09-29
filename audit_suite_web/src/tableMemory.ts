export type TableState = { query: string; page: number; sort: string };
export function createTableMemory() {
  const entries = new Map<string, TableState>();
  const restorations = new Map<string, TableState>();
  const listeners = new Map<string, Set<(state: TableState) => void>>();
  return {
    read(key: string): TableState {
      return { ...(entries.get(key) ?? { query: "", page: 0, sort: "" }) };
    },
    restoration(key: string): TableState | null {
      const value = restorations.get(key);
      return value ? { ...value } : null;
    },
    dismissRestoration(key: string) {
      restorations.delete(key);
    },
    subscribe(key: string, listener: (state: TableState) => void) {
      const current = listeners.get(key) ?? new Set();
      current.add(listener);
      listeners.set(key, current);
      return () => {
        current.delete(listener);
        if (!current.size) listeners.delete(key);
      };
    },
    restore(key: string, state: TableState) {
      this.write(key, state);
      restorations.set(key, this.read(key));
      for (const listener of listeners.get(key) ?? []) listener(this.read(key));
    },
    write(key: string, state: TableState) {
      entries.delete(key);
      entries.set(key, {
        query: state.query.slice(0, 1000),
        page: Number.isSafeInteger(state.page) ? Math.max(0, state.page) : 0,
        sort: state.sort.slice(0, 200),
      });
      if (entries.size > 100) {
        const oldest = entries.keys().next().value!;
        entries.delete(oldest);
        restorations.delete(oldest);
      }
    },
  };
}
