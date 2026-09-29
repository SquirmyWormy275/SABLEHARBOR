export type CensusQuery = {
  version_policy: "ALL_VISIBLE_VERSIONS" | "LATEST_VISIBLE_PER_RECORD";
  event_window: { start: string; end: string };
  unknown_event_policy: "EXCLUDE" | "INCLUDE_UNDATED_STRATUM";
};
function instant(value: string): number {
  const match =
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})$/.exec(
      value,
    );
  if (!match)
    throw Error(
      "Use explicit-offset ISO timestamps, including Z or a UTC offset.",
    );
  const [, y, m, d, h, min, sec] = match,
    year = Number(y),
    month = Number(m),
    day = Number(d),
    days = [
      31,
      year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0) ? 29 : 28,
      31,
      30,
      31,
      30,
      31,
      31,
      30,
      31,
      30,
      31,
    ];
  if (
    month < 1 ||
    month > 12 ||
    day < 1 ||
    day > days[month - 1] ||
    Number(h) > 23 ||
    Number(min) > 59 ||
    Number(sec ?? 0) > 59 ||
    !Number.isFinite(Date.parse(value))
  )
    throw Error("Use valid calendar instants.");
  return Date.parse(value);
}
export function censusQuery(
  versionPolicy: string,
  start: string,
  end: string,
  unknownPolicy: string,
): CensusQuery {
  if (
    !["ALL_VISIBLE_VERSIONS", "LATEST_VISIBLE_PER_RECORD"].includes(
      versionPolicy,
    ) ||
    !["EXCLUDE", "INCLUDE_UNDATED_STRATUM"].includes(unknownPolicy)
  )
    throw Error("Choose an explicit version and undated-record policy.");
  if (instant(start) >= instant(end))
    throw Error("The exclusive window end must be after its start.");
  return {
    version_policy: versionPolicy as CensusQuery["version_policy"],
    event_window: { start, end },
    unknown_event_policy: unknownPolicy as CensusQuery["unknown_event_policy"],
  };
}
