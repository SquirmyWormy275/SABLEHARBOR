export type AuthoredNode = {
  id: string;
  kind: string;
  source_id?: string;
  source_pointer: string;
  value: unknown;
};
export type AuthoredEdge = {
  from: string;
  to: string;
  relation: string;
  source_pointer: string;
};
export type AuthoredGraph = { nodes: AuthoredNode[]; edges: AuthoredEdge[] };

const roots: Record<string, string> = {
  fact: "facts",
  artifact: "artifacts",
  event: "events",
  path: "playable_paths",
  actor: "actor_knowledge",
};
const object = (v: unknown): v is Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v);

/** Resolve only own JSON fields in the preserved explanation, never prototype paths. */
export function authoredValue(explanation: unknown, pointer: string): unknown {
  if (!pointer.startsWith("/") || pointer.length > 1024) return undefined;
  let value: unknown = explanation;
  for (const raw of pointer.slice(1).split("/")) {
    if (/~(?![01])/.test(raw)) return undefined;
    const key = raw.replaceAll("~1", "/").replaceAll("~0", "~");
    if (["__proto__", "prototype", "constructor"].includes(key))
      return undefined;
    if (Array.isArray(value)) {
      if (!/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= value.length)
        return undefined;
      value = value[Number(key)];
    } else if (object(value) && Object.hasOwn(value, key)) value = value[key];
    else return undefined;
  }
  return value;
}

/** A display projection of exact authored edges; never infer links from prose or IDs. */
export function authoredGraph(
  graph: unknown,
  explanation: unknown,
): AuthoredGraph | null {
  if (
    !object(graph) ||
    graph.edge_semantics !== "AUTHORED_REFERENCES_ONLY_NOT_CORROBORATION" ||
    !Array.isArray(graph.nodes) ||
    graph.nodes.length > 256 ||
    !Array.isArray(graph.edges) ||
    graph.edges.length > 1024
  )
    return null;
  const nodes: AuthoredNode[] = [];
  const ids = new Set<string>();
  for (const n of graph.nodes) {
    if (
      !object(n) ||
      typeof n.id !== "string" ||
      !n.id ||
      n.id.length > 256 ||
      ids.has(n.id) ||
      typeof n.kind !== "string" ||
      !Object.hasOwn(roots, n.kind) ||
      typeof n.source_pointer !== "string" ||
      !new RegExp(`^/${roots[n.kind]}/(0|[1-9][0-9]*)$`).test(
        n.source_pointer,
      ) ||
      (n.source_id !== undefined && typeof n.source_id !== "string")
    )
      return null;
    const value = authoredValue(explanation, n.source_pointer);
    if (value === undefined) return null;
    ids.add(n.id);
    nodes.push({
      id: n.id,
      kind: n.kind,
      source_id: n.source_id as string | undefined,
      source_pointer: n.source_pointer,
      value,
    });
  }
  const edges: AuthoredEdge[] = [];
  for (const e of graph.edges) {
    if (
      !object(e) ||
      typeof e.from !== "string" ||
      typeof e.to !== "string" ||
      !ids.has(e.from) ||
      !ids.has(e.to) ||
      typeof e.relation !== "string" ||
      !e.relation ||
      e.relation.length > 128 ||
      typeof e.source_pointer !== "string" ||
      authoredValue(explanation, e.source_pointer) === undefined
    )
      return null;
    edges.push({
      from: e.from,
      to: e.to,
      relation: e.relation,
      source_pointer: e.source_pointer,
    });
  }
  return { nodes, edges };
}

export function authoredTiming(node: AuthoredNode): string {
  const v = node.value;
  if (node.kind !== "event" || !object(v)) return "No authored event timing";
  const trigger =
    typeof v.trigger === "string" ? v.trigger : "Unspecified trigger";
  const offset = v.offset_business_days;
  return typeof offset === "number" && Number.isSafeInteger(offset)
    ? `${trigger} · ${offset} business days from this trigger`
    : `${trigger} · timing not authored`;
}
