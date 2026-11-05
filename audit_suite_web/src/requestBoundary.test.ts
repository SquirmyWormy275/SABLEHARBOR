import { describe, expect, it } from "vitest";
import { requestBoundaryFields } from "./requestBoundary";

describe("PBC request boundary", () => {
  it("asks for a scoped boundary only when the engagement has several", () => {
    expect(requestBoundaryFields(undefined)).toEqual([]);
    expect(requestBoundaryFields(["corporate"])).toEqual([]);
    const [field] = requestBoundaryFields(["RUNTIME-RENO-COLO", "corporate"]);
    expect(field).toMatchObject({
      name: "boundary_id",
      type: "select",
      required: true,
    });
    expect(field.options?.map((o) => o.value)).toEqual([
      "RUNTIME-RENO-COLO",
      "corporate",
    ]);
  });
});
