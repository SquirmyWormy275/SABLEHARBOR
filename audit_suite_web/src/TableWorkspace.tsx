import { createContext, useContext, useState, type ReactNode } from "react";
import { createTableMemory } from "./tableMemory";
const Context = createContext<ReturnType<typeof createTableMemory> | null>(
  null,
);
/** App keys this provider by viewer, engagement, permissions and scope. No records are stored. */
export function TableWorkspace({ children }: { children: ReactNode }) {
  const [memory] = useState(createTableMemory);
  return <Context.Provider value={memory}>{children}</Context.Provider>;
}
export function useTableMemory() {
  return useContext(Context);
}
