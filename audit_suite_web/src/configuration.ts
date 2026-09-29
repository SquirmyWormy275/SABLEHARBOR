import selectors from "./selectors.json";
export { selectors };
export type OptionConfig = {
  enabled: boolean;
  authoring: "Standard" | "Custom";
  intensity: number;
  share: number;
  frequency: number;
  severity: number;
  count: number;
  custom_text: string;
  type: string;
};
export type Configuration = {
  parents: Record<string, boolean>;
  options: Record<string, OptionConfig>;
  incomplete_percent: number;
  disagreement_frequency: number;
  disagreement_severity: number;
  types: Record<string, string>;
};
export const initialConfig = (): Configuration => ({
  parents: {},
  options: {},
  incomplete_percent: 0,
  disagreement_frequency: 1,
  disagreement_severity: 50,
  types: {},
});
export const optionDefault = (): OptionConfig => ({
  enabled: false,
  authoring: "Standard",
  intensity: 50,
  share: 0,
  frequency: 25,
  severity: 50,
  count: 1,
  custom_text: "",
  type: "FICTIONAL_RULEBOOK",
});
export function configErrors(config: Configuration): string[] {
  const errors: string[] = [];
  const affected = selectors
    .find((s) => s.id === "MM-02")!
    .options.filter((o) => config.options[o.id]?.enabled);
  if (config.parents["MM-02"] && config.incomplete_percent > 0) {
    if (!affected.length)
      errors.push("Select at least one incomplete-evidence option.");
    if (affected.reduce((n, o) => n + config.options[o.id].share, 0) !== 100)
      errors.push(
        "Incomplete-evidence shares must total 100% of the affected controls.",
      );
  }
  for (const parent of selectors) {
    if (
      config.parents[parent.id] &&
      parent.id !== "MM-08" &&
      !parent.options.some((o) => config.options[o.id]?.enabled)
    )
      errors.push(`Choose an option for ${parent.name}.`);
  }
  return errors;
}
export function normalizedShares(config: Configuration): Configuration {
  const ids = selectors
    .find((s) => s.id === "MM-02")!
    .options.filter((o) => config.options[o.id]?.enabled)
    .map((o) => o.id)
    .sort();
  if (!ids.length) return config;
  const sum = ids.reduce(
    (n, id) => n + Math.max(0, config.options[id].share),
    0,
  );
  const entries = ids.map((id) => {
    const exact = sum
      ? (100 * Math.max(0, config.options[id].share)) / sum
      : 100 / ids.length;
    return {
      id,
      share: Math.floor(exact),
      remainder: exact - Math.floor(exact),
    };
  });
  let left = 100 - entries.reduce((n, v) => n + v.share, 0);
  entries.sort((a, b) => b.remainder - a.remainder || a.id.localeCompare(b.id));
  for (const entry of entries) {
    if (left-- > 0) entry.share++;
  }
  return {
    ...config,
    options: {
      ...config.options,
      ...Object.fromEntries(
        entries.map(({ id, share }) => [id, { ...config.options[id], share }]),
      ),
    },
  };
}
export function serializeConfiguration(config: Configuration) {
  return {
    selections: selectors
      .filter((s) => config.parents[s.id])
      .flatMap((s) =>
        s.id === "MM-08"
          ? [
              {
                selector_id: s.id,
                option_id: "",
                authoring_mode: (
                  config.options[s.id]?.authoring ?? "Standard"
                ).toUpperCase(),
                parameters: {
                  frequency: config.disagreement_frequency,
                  severity: config.disagreement_severity,
                },
                custom_text: config.options[s.id]?.custom_text ?? "",
              },
            ]
          : s.options
              .filter((o) => config.options[o.id]?.enabled)
              .map((o) => {
                const value = config.options[o.id];
                return {
                  selector_id: s.id,
                  option_id: o.id,
                  authoring_mode: value.authoring.toUpperCase(),
                  parameters: {
                    ...(s.id === "MM-03" ? { intensity: value.intensity } : {}),
                    ...(s.id === "MM-09" ? { frequency: value.frequency } : {}),
                    ...(["MM-09", "MM-11", "MM-14"].includes(s.id)
                      ? { severity: value.severity }
                      : {}),
                    ...(s.id === "MM-10" ? { count: value.count } : {}),
                    ...(s.id === "MM-13" ? { type: value.type } : {}),
                    ...(["MM-14", "MM-15"].includes(s.id) && config.types[s.id]
                      ? { type: config.types[s.id] }
                      : {}),
                  },
                  custom_text: value.custom_text,
                };
              }),
      ),
    ...(config.parents["MM-02"]
      ? {
          incomplete_evidence: {
            overall: config.incomplete_percent,
            shares: Object.fromEntries(
              selectors
                .find((s) => s.id === "MM-02")!
                .options.filter(
                  (o) =>
                    config.parents["MM-02"] && config.options[o.id]?.enabled,
                )
                .map((o) => [o.id, config.options[o.id].share]),
            ),
          },
        }
      : {}),
  };
}
