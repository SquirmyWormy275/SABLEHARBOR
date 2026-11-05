import type { Field } from "./components";

// The service assigns the only scoped boundary itself. With several, a request
// must name one before company census or population collection can use it.
export function requestBoundaryFields(boundaries?: string[]): Field[] {
  return boundaries && boundaries.length > 1
    ? [
        {
          name: "boundary_id",
          label: "Boundary",
          type: "select",
          required: true,
          options: boundaries.map((value) => ({ value, label: value })),
        },
      ]
    : [];
}
