export type TableState = { query: string; page: number; sort: string };
export function createTableMemory() {
  const entries = new Map<string, TableState>();
  return {
    read(key: string): TableState {
      return { ...(entries.get(key) ?? { query: "", page: 0, sort: "" }) };
    },
    write(key: string, state: TableState) {
      entries.delete(key);
      entries.set(key, {
        query: state.query.slice(0, 1000),
        page: Number.isSafeInteger(state.page) ? Math.max(0, state.page) : 0,
        sort: state.sort.slice(0, 200),
      });
      if (entries.size > 100) entries.delete(entries.keys().next().value!);
    },
  };
}
