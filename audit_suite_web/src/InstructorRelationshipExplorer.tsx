import { useMemo, useState, type ReactNode } from "react";
import { authoredGraph, authoredTiming } from "./instructorGraph";
import "./instructorGraph.css";

const names: Record<string, string> = {
  fact: "Facts",
  actor: "Actors",
  event: "Events",
  artifact: "Artifacts",
  path: "Discovery paths",
};

export function InstructorRelationshipExplorer({
  graph: raw,
  explanation,
  renderValue,
}: {
  graph: unknown;
  explanation: unknown;
  renderValue: (value: unknown) => ReactNode;
}) {
  const graph = useMemo(
    () => authoredGraph(raw, explanation),
    [raw, explanation],
  );
  const [selected, setSelected] = useState("");
  const [query, setQuery] = useState("");
  const [trail, setTrail] = useState<string[]>([]);
  if (!graph)
    return (
      <p>
        The authored relationship map cannot be resolved exactly. The preserved
        source remains available below.
      </p>
    );
  const node = graph.nodes.find((n) => n.id === selected);
  const links = node
    ? graph.edges.filter((e) => e.from === node.id || e.to === node.id)
    : [];
  const matching = graph.nodes.filter((n) =>
    `${n.id} ${n.source_id ?? ""} ${n.kind}`
      .toLowerCase()
      .includes(query.trim().toLowerCase()),
  );
  const choose = (id: string) => {
    if (id === selected) return;
    setTrail((t) => (selected ? [...t, selected].slice(-50) : t));
    setSelected(id);
  };
  return (
    <section
      className="authored-explorer"
      aria-label="Authored relationship explorer"
    >
      <h4>Explore the authored relationships</h4>
      <p>
        Follow explicit source references. These links describe the scenario
        author’s account; they do not establish corroboration or what a learner
        discovered.
      </p>
      <label>
        Find a relationship node
        <input value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>
      <p>
        {matching.length} of {graph.nodes.length} nodes · {graph.edges.length}{" "}
        authored links
      </p>
      <div className="authored-node-groups">
        {Object.entries(names).map(([kind, name]) => (
          <section key={kind} aria-label={name + " in authored map"}>
            <h5>{name}</h5>
            {matching
              .filter((n) => n.kind === kind)
              .map((n) => (
                <button
                  key={n.id}
                  aria-pressed={n.id === selected}
                  onClick={() => choose(n.id)}
                >
                  {n.id}
                </button>
              ))}
            {!matching.some((n) => n.kind === kind) && <p>No matching nodes</p>}
          </section>
        ))}
      </div>
      <details>
        <summary>Event timing by trigger</summary>
        <p>
          Offsets are relative to their named trigger. Different triggers do not
          establish a shared calendar or prove an event occurred. Entries retain
          source order.
        </p>
        <ol className="authored-events">
          {graph.nodes
            .filter((n) => n.kind === "event")
            .map((n) => (
              <li key={n.id}>
                <button
                  aria-pressed={n.id === selected}
                  onClick={() => choose(n.id)}
                >
                  {n.id}
                </button>
                <p>{authoredTiming(n)}</p>
              </li>
            ))}
        </ol>
      </details>
      {node ? (
        <article aria-label="Selected authored node">
          <div className="actions">
            <button
              disabled={!trail.length}
              onClick={() => {
                setSelected(trail[trail.length - 1]);
                setTrail((t) => t.slice(0, -1));
              }}
            >
              Back through relationships
            </button>
            <button
              onClick={() => {
                setSelected("");
                setTrail([]);
              }}
            >
              Clear node selection
            </button>
          </div>
          <h5>{node.id}</h5>
          <p>
            Exact source reference: <code>{node.source_pointer}</code>
          </p>
          {!matching.some((n) => n.id === node.id) && (
            <p>
              The selected node is outside the current search. Its selection is
              retained.
            </p>
          )}
          {renderValue(node.value)}
          <h5>Explicit links for this node</h5>
          {!links.length && (
            <p>
              No explicit links were authored for this node. Narrative
              references may still exist in the preserved source.
            </p>
          )}
          <ul>
            {links.map((e, i) => (
              <li key={i}>
                <span>
                  {e.from === node.id ? "Outgoing" : "Incoming"} ·{" "}
                  {e.relation.replaceAll("_", " ")}
                </span>
                {" → "}
                <button
                  onClick={() => choose(e.from === node.id ? e.to : e.from)}
                >
                  {e.from === node.id ? e.to : e.from}
                </button>
                <p>
                  Authored reference: <code>{e.source_pointer}</code>
                </p>
              </li>
            ))}
          </ul>
        </article>
      ) : (
        <p>
          Select a node to inspect its exact source and follow incoming or
          outgoing links.
        </p>
      )}
    </section>
  );
}
