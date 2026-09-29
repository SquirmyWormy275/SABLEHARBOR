export type KeyReview = {
  professional: string;
  causal_validation: string;
  grading: string;
  gaps: string[];
};
export type KeyEntry = {
  id: string;
  raw_sha256: string;
  canonical_sha256: string;
  key_sha256: string;
  review: KeyReview;
};
export type KeyContext = {
  status: "UNBOUND_REFERENCE_LIBRARY";
  binding: { status: "NOT_BOUND"; engagement_id: string };
  archive: { sha256: string };
};
export type InstructorIndex = KeyContext & {
  audience: "INSTRUCTOR_ONLY";
  required: number;
  migrated: number;
  entries: KeyEntry[];
};
export type InstructorDetail = KeyContext & {
  key: {
    schema: "PRIVATE_INSTRUCTOR_KEY_V1";
    audience: "INSTRUCTOR_ONLY";
    id: string;
    source: {
      raw_sha256: string;
      canonical_sha256: string;
      schema_version: string;
    };
    review: KeyReview;
    explanation: {
      title: string;
      mechanism: unknown;
      facts: unknown[];
      actor_knowledge: unknown[];
      artifacts: unknown[];
      events: unknown[];
      playable_paths: unknown[];
      rubric: {
        supported_conclusions: unknown[];
        acceptable_alternatives: unknown[];
        unsupported_guesses: unknown[];
      };
    };
    graph: unknown;
  };
};
export const keyOption = (id: string) => id.replace(/\.V\d+$/, "");
export const keySelector = (id: string) => id.split(".")[0];
export function filterKeys(
  entries: KeyEntry[],
  f: { query: string; selector: string; option: string; review: string },
) {
  const q = f.query.trim().toLowerCase();
  return entries.filter(
    (e) =>
      (f.selector === "all" || keySelector(e.id) === f.selector) &&
      (f.option === "all" || keyOption(e.id) === f.option) &&
      (f.review === "all" || e.review.professional === f.review) &&
      (!q ||
        [e.id, e.review.professional, ...e.review.gaps]
          .join(" ")
          .toLowerCase()
          .includes(q)),
  );
}
export function assertKeyContext(v: KeyContext, id: string) {
  if (
    v.status !== "UNBOUND_REFERENCE_LIBRARY" ||
    v.binding?.status !== "NOT_BOUND" ||
    v.binding.engagement_id !== id ||
    !/^[a-f0-9]{64}$/.test(v.archive?.sha256 ?? "")
  )
    throw Error("Protected source context does not match this engagement.");
}
export function assertKeyDetail(
  v: InstructorDetail,
  e: KeyEntry,
  id: string,
  archive: string,
) {
  assertKeyContext(v, id);
  const k = v.key;
  if (
    v.archive.sha256 !== archive ||
    k?.schema !== "PRIVATE_INSTRUCTOR_KEY_V1" ||
    k.audience !== "INSTRUCTOR_ONLY" ||
    k.id !== e.id ||
    k.source.raw_sha256 !== e.raw_sha256 ||
    k.source.canonical_sha256 !== e.canonical_sha256
  )
    throw Error("Explanation differs from the selected immutable source.");
}
