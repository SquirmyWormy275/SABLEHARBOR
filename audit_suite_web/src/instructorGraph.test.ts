import { describe, expect, it } from "vitest";
import {
  authoredGraph,
  authoredTiming,
  authoredValue,
} from "./instructorGraph";

const explanation = {
  facts: [{ id: "F1", statement: "Authored statement" }],
  actor_knowledge: [{ knows_fact_ids: ["F1"] }],
  events: [{ trigger: "FOLLOWUP", offset_business_days: 1 }],
  artifacts: [],
  playable_paths: [{ id: "investigate", actions: ["Narrative F1"] }],
};
const graph = {
  edge_semantics: "AUTHORED_REFERENCES_ONLY_NOT_CORROBORATION",
  nodes: [
    {
      id: "fact:F1",
      kind: "fact",
      source_id: "F1",
      source_pointer: "/facts/0",
    },
    { id: "actor:0", kind: "actor", source_pointer: "/actor_knowledge/0" },
    { id: "event:E1", kind: "event", source_pointer: "/events/0" },
    {
      id: "path:investigate",
      kind: "path",
      source_pointer: "/playable_paths/0",
    },
  ],
  edges: [
    {
      from: "actor:0",
      to: "fact:F1",
      relation: "AUTHORED_KNOWLEDGE",
      source_pointer: "/actor_knowledge/0/knows_fact_ids/0",
    },
  ],
};

describe("exact authored relationship projection", () => {
  it("keeps source order and explicit edges without inferring a narrative link", () => {
    const result = authoredGraph(graph, explanation)!;
    expect(result.nodes.map((n) => n.id)).toEqual(graph.nodes.map((n) => n.id));
    expect(result.edges).toEqual(graph.edges);
    expect(result.edges.some((e) => e.from === "path:investigate")).toBe(false);
    expect(result.nodes[0].value).toEqual(explanation.facts[0]);
  });
  it("rejects duplicate identities and dangling endpoints", () => {
    expect(
      authoredGraph(
        { ...graph, nodes: [...graph.nodes, graph.nodes[0]] },
        explanation,
      ),
    ).toBeNull();
    expect(
      authoredGraph(
        { ...graph, edges: [{ ...graph.edges[0], to: "absent" }] },
        explanation,
      ),
    ).toBeNull();
  });
  it("rejects a kind mismatched source pointer or nonexistent source", () => {
    for (const source_pointer of [
      "/events/0",
      "/facts/9",
      "/facts/01",
      "/facts/0/statement",
    ]) {
      expect(
        authoredGraph(
          { ...graph, nodes: [{ ...graph.nodes[0], source_pointer }] },
          explanation,
        ),
      ).toBeNull();
    }
    expect(
      authoredGraph(
        {
          ...graph,
          edges: [{ ...graph.edges[0], source_pointer: "/missing" }],
        },
        explanation,
      ),
    ).toBeNull();
  });
  it("does not accept another graph semantic or an unbounded graph", () => {
    expect(
      authoredGraph(
        { ...graph, edge_semantics: "VERIFIED_CAUSALITY" },
        explanation,
      ),
    ).toBeNull();
    expect(
      authoredGraph(
        { ...graph, nodes: Array(257).fill(graph.nodes[0]) },
        explanation,
      ),
    ).toBeNull();
    expect(
      authoredGraph(
        { ...graph, edges: Array(1025).fill(graph.edges[0]) },
        explanation,
      ),
    ).toBeNull();
  });
  it("resolves escaped own fields and preserves authored false/null values", () => {
    expect(authoredValue({ "a/b": { "c~d": false } }, "/a~1b/c~0d")).toBe(
      false,
    );
    expect(authoredValue({ facts: [null] }, "/facts/0")).toBeNull();
    for (const p of [
      "/__proto__",
      "/constructor",
      "/facts/length",
      "/facts/-1",
      "/facts/00",
      "/facts/0/~9",
    ]) {
      expect(authoredValue(explanation, p)).toBeUndefined();
    }
    expect(
      authoredValue(Object.create({ inherited: "hidden" }), "/inherited"),
    ).toBeUndefined();
  });
  it("labels business-day timing relative to its own trigger, never as a shared date", () => {
    const event = authoredGraph(graph, explanation)!.nodes[2];
    expect(authoredTiming(event)).toBe(
      "FOLLOWUP · 1 business days from this trigger",
    );
    expect(
      authoredTiming({
        ...event,
        value: { trigger: "REQUEST", offset_business_days: "1" },
      }),
    ).toBe("REQUEST · timing not authored");
  });
});
