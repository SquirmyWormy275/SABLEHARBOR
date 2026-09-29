import type { Engagement, Row } from "./api";
import { populationLineage } from "./populationLineage";
export default function PopulationLineage({
  engagement,
  kind,
  row,
  onOpen,
}: {
  engagement: Engagement;
  kind: string;
  row: Row;
  onOpen: (reference: Row) => void;
}) {
  const value = populationLineage(engagement, kind, row);
  return (
    <section aria-label="Population and selection lineage">
      <h3>Trace this selection and its support</h3>
      <p>
        These links follow recorded population versions, source hashes and
        explicit workpaper evidence references. A shared original does not
        establish that selected items were tested.
      </p>
      {value.population && (
        <p>
          Population {value.population.id} · Version{" "}
          {String(value.population.version)} · Reliability{" "}
          {String(value.population.status ?? "not recorded")}
        </p>
      )}
      <ul>
        {value.links.map((link, index) => (
          <li key={index}>
            <button type="button" onClick={() => onOpen(link.reference)}>
              {link.label}
            </button>
          </li>
        ))}
      </ul>
      {value.unavailable.map((text, index) => (
        <p key={index}>{text}</p>
      ))}
      {value.population && value.workpaperLinks === 0 && (
        <p>
          No workpaper version explicitly references this pinned population
          original. Similar control IDs or titles are not treated as links.
        </p>
      )}
    </section>
  );
}
