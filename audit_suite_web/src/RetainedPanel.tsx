import { useEffect, useState, type ReactNode } from "react";

/** Lazy first visit; caller's authorization-context key discards retained state on context change. */
export default function RetainedPanel({
  active,
  children,
}: {
  active: boolean;
  children: ReactNode;
}) {
  const [visited, setVisited] = useState(active);
  useEffect(() => {
    if (active) setVisited(true);
  }, [active]);
  return <div hidden={!active}>{(active || visited) && children}</div>;
}
