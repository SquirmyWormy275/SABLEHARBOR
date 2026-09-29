import ScopeDetails from "./ScopeDetails";
import { useState } from "react";
import type { Bootstrap, Scope } from "./api";
import { str } from "./api";
import {
  serializeConfiguration,
  selectors,
  initialConfig,
  optionDefault,
  configErrors,
  normalizedShares,
  type Configuration,
  type OptionConfig,
} from "./configuration";
export default function Setup({
  bootstrap,
  busy,
  onCreate,
  onCancel,
}: {
  bootstrap: Bootstrap;
  busy: boolean;
  onCreate: (payload: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}) {
  const [step, setStep] = useState(0),
    [discipline, setDiscipline] = useState("IT"),
    [mode, setMode] = useState("Clean"),
    [title, setTitle] = useState("Sable Harbor reference engagement"),
    [config, setConfig] = useState<Configuration>(initialConfig),
    [expanded, setExpanded] = useState("MM-01");
  const [scope, setScope] = useState<Scope>({
    programs: [],
    period_start: "2027-01-01",
    period_end: "2027-12-31",
    fieldwork_start: "2028-01-01",
    timezone: "UTC",
    report_type: "Type 2",
    boundaries: (bootstrap.boundaries ?? [])
      .filter((b) => /corporate|reno|boise/i.test(b.id + " " + String(b.title)))
      .map((b) => b.id),
    reporting_basis: "",
    accounts: [],
    materiality_rationale: "",
  });
  const errors = mode === "Messy" ? configErrors(config) : [];
  const option = (id: string) => config.options[id] ?? optionDefault();
  function update(id: string, value: Partial<OptionConfig>) {
    setConfig({
      ...config,
      options: { ...config.options, [id]: { ...option(id), ...value } },
    });
  }
  function range(
    label: string,
    value: number,
    set: (n: number) => void,
    unit = "%",
  ) {
    return (
      <label className="range-field">
        {label}
        <span>
          <input
            type="range"
            min="0"
            max="100"
            value={value}
            onChange={(e) => set(Number(e.target.value))}
          />
          <output>
            {value}
            {unit}
          </output>
        </span>
      </label>
    );
  }
  return (
    <main className="setup">
      <header className="setup-heading">
        <p className="eyebrow">New engagement</p>
        <h1>
          Set the terms.
          <br />
          Then follow the evidence.
        </h1>
        <p>
          A fictional company. A complete engagement. Your methodology and
          judgment.
        </p>
      </header>
      <nav className="steps" aria-label="Setup progress">
        {[
          "Discipline & mode",
          "Scenario configuration",
          "Engagement scope",
        ].map((label, i) => (
          <button
            key={label}
            className={step === i ? "current" : ""}
            disabled={i > step}
            onClick={() => setStep(i)}
          >
            <b>0{i + 1}</b>
            {label}
          </button>
        ))}
      </nav>
      <section className="setup-body">
        {step === 0 ? (
          <>
            <h2>What kind of work will you undertake?</h2>
            <div className="choice-grid">
              {[
                [
                  "IT",
                  "IT & controls",
                  "Service organizations, systems and common controls.",
                ],
                [
                  "Financial",
                  "Financial statement audit",
                  "Accounts, assertions, substantive work and IT dependencies.",
                ],
              ].map(([id, label, description]) => (
                <button
                  key={id}
                  className={`choice ${discipline === id ? "selected" : ""}`}
                  aria-pressed={discipline === id}
                  onClick={() => setDiscipline(id)}
                >
                  <strong>{label}</strong>
                  <span>{description}</span>
                </button>
              ))}
            </div>
            <h2>Choose the company’s circumstances</h2>
            <div className="choice-grid">
              {[
                [
                  "Clean",
                  "Coherent records and timely cooperation. Ordinary inquiry and testing still matter.",
                ],
                [
                  "Messy",
                  "Authored challenges across people, evidence, systems and accounting.",
                ],
              ].map(([id, description]) => (
                <button
                  key={id}
                  className={`choice ${mode === id ? "selected" : ""}`}
                  aria-pressed={mode === id}
                  onClick={() => setMode(id)}
                >
                  <strong>{id}</strong>
                  <span>{description}</span>
                </button>
              ))}
            </div>
          </>
        ) : step === 1 ? (
          <>
            <h2>
              {mode === "Clean"
                ? "A coherent starting point"
                : "Configure the challenge"}
            </h2>
            {mode === "Clean" ? (
              <p>
                Clean mode uses complete, consistent synthetic records without
                deliberate challenge injections. You still determine what to
                request, test and conclude.
              </p>
            ) : (
              <>
                <p className="muted">
                  Standard draws from the authored library. Custom is
                  experimental, AI-assisted authoring. These choices are visible
                  to the trainer and are withheld from blind learners.
                </p>
                <div className="selector-layout">
                  <nav aria-label="Challenge families">
                    {selectors.map((s) => (
                      <button
                        key={s.id}
                        className={expanded === s.id ? "current" : ""}
                        onClick={() => setExpanded(s.id)}
                      >
                        <span>{s.id}</span>
                        {s.name}
                        {config.parents[s.id] && <b aria-label="Enabled">●</b>}
                      </button>
                    ))}
                  </nav>
                  <div className="selector-detail">
                    {selectors
                      .filter((s) => s.id === expanded)
                      .map((s) => (
                        <section key={s.id}>
                          <label className="toggle-heading">
                            <input
                              type="checkbox"
                              checked={!!config.parents[s.id]}
                              onChange={(e) =>
                                setConfig({
                                  ...config,
                                  parents: {
                                    ...config.parents,
                                    [s.id]: e.target.checked,
                                  },
                                })
                              }
                            />
                            <h3>{s.name}</h3>
                          </label>
                          {s.id === "MM-02" && (
                            <>
                              {range(
                                "Share of eligible control implementations affected",
                                config.incomplete_percent,
                                (n) =>
                                  setConfig({
                                    ...config,
                                    incomplete_percent: n,
                                  }),
                              )}
                              <p className="hint">
                                Subcategory shares apply within that affected
                                group, not to the whole engagement.
                              </p>
                              <button
                                onClick={() =>
                                  setConfig(normalizedShares(config))
                                }
                              >
                                Normalize selected shares to 100%
                              </button>
                            </>
                          )}
                          {s.id === "MM-08" && (
                            <>
                              <label>
                                Authoring route
                                <select
                                  value={option(s.id).authoring}
                                  onChange={(event) =>
                                    update(s.id, {
                                      authoring: event.target.value as
                                        "Standard" | "Custom",
                                    })
                                  }
                                >
                                  <option>Standard</option>
                                  <option>Custom</option>
                                </select>
                              </label>
                              {option(s.id).authoring === "Custom" && (
                                <label>
                                  Custom disagreement intent
                                  <textarea
                                    value={option(s.id).custom_text}
                                    onChange={(event) =>
                                      update(s.id, {
                                        custom_text: event.target.value,
                                      })
                                    }
                                    maxLength={8000}
                                  />
                                  <small>
                                    Saved as a draft; private model authoring,
                                    validation and instructor acceptance precede
                                    generation.
                                  </small>
                                </label>
                              )}
                              {range(
                                "Frequency of eligible owner interactions",
                                config.disagreement_frequency,
                                (n) =>
                                  setConfig({
                                    ...config,
                                    disagreement_frequency: n,
                                  }),
                              )}
                              {range(
                                "Severity",
                                config.disagreement_severity,
                                (n) =>
                                  setConfig({
                                    ...config,
                                    disagreement_severity: n,
                                  }),
                                " / 100",
                              )}
                              <p className="hint">
                                Frequency and severity are independent. A rare,
                                severe disagreement is supported. This family
                                has no submenu.
                              </p>
                            </>
                          )}
                          {["MM-14", "MM-15"].includes(s.id) && (
                            <label>
                              {s.id === "MM-14"
                                ? "Affected information"
                                : "System type"}
                              <select
                                value={config.types[s.id] ?? ""}
                                onChange={(e) =>
                                  setConfig({
                                    ...config,
                                    types: {
                                      ...config.types,
                                      [s.id]: e.target.value,
                                    },
                                  })
                                }
                              >
                                <option value="">Select a type…</option>
                                {(s.id === "MM-14"
                                  ? [
                                      "Customer information",
                                      "Accounting / financial records",
                                      "Workforce / payroll data",
                                      "Identity / credential records",
                                      "Source code / configuration",
                                      "Supplier-held records",
                                      "Backup / archive",
                                    ]
                                  : [
                                      "Legacy ERP / general ledger",
                                      "Custom accounting / billing",
                                      "Payroll / HR",
                                      "Inventory / fixed assets",
                                      "Mainframe / batch",
                                      "On-premises identity",
                                      "Ticket / change system",
                                      "Database / reporting",
                                      "Backup / archive",
                                      "File transfer / integration",
                                    ]
                                ).map((t) => (
                                  <option
                                    key={t}
                                    disabled={
                                      t === "Financial statement audit" &&
                                      discipline !== "Financial"
                                    }
                                  >
                                    {t}
                                  </option>
                                ))}
                              </select>
                            </label>
                          )}
                          {s.options.map((o) => (
                            <article className="option" key={o.id}>
                              <label className="option-toggle">
                                <input
                                  type="checkbox"
                                  disabled={!config.parents[s.id]}
                                  checked={option(o.id).enabled}
                                  onChange={(e) =>
                                    update(o.id, { enabled: e.target.checked })
                                  }
                                />
                                <strong>{o.label}</strong>
                              </label>
                              <p>{o.description}</p>
                              {option(o.id).enabled && (
                                <div className="option-settings">
                                  <label>
                                    Authoring route
                                    <select
                                      value={option(o.id).authoring}
                                      onChange={(e) =>
                                        update(o.id, {
                                          authoring: e.target.value as
                                            "Standard" | "Custom",
                                        })
                                      }
                                    >
                                      <option>Standard</option>
                                      <option>Custom</option>
                                    </select>
                                  </label>
                                  {s.id === "MM-02" &&
                                    range(
                                      "Share of affected group",
                                      option(o.id).share,
                                      (n) => update(o.id, { share: n }),
                                    )}
                                  {s.id === "MM-03" &&
                                    range(
                                      "Independent behavioral intensity",
                                      option(o.id).intensity,
                                      (n) => update(o.id, { intensity: n }),
                                      " / 100",
                                    )}
                                  {["MM-09", "MM-11", "MM-14"].includes(s.id) &&
                                    range(
                                      "Severity",
                                      option(o.id).severity,
                                      (n) => update(o.id, { severity: n }),
                                      " / 100",
                                    )}
                                  {s.id === "MM-09" &&
                                    range(
                                      "Frequency of eligible third-party requests",
                                      option(o.id).frequency,
                                      (n) => update(o.id, { frequency: n }),
                                    )}
                                  {s.id === "MM-10" && (
                                    <label>
                                      Number of change events
                                      <input
                                        type="number"
                                        min="1"
                                        max="100"
                                        value={option(o.id).count}
                                        onChange={(e) =>
                                          update(o.id, {
                                            count: Number(e.target.value),
                                          })
                                        }
                                      />
                                    </label>
                                  )}
                                  {s.id === "MM-13" && (
                                    <label>
                                      Rule authority
                                      <select
                                        value={option(o.id).type}
                                        onChange={(e) =>
                                          update(o.id, { type: e.target.value })
                                        }
                                      >
                                        <option value="FICTIONAL_RULEBOOK">
                                          Explicit fictional rulebook
                                        </option>
                                        <option value="REAL_SOURCE">
                                          Verified real source
                                        </option>
                                      </select>
                                    </label>
                                  )}
                                  {option(o.id).authoring === "Custom" && (
                                    <div className="experimental">
                                      <strong>
                                        Experimental custom authoring
                                      </strong>
                                      <label>
                                        Describe the situation in your own words
                                        <textarea
                                          rows={5}
                                          value={option(o.id).custom_text}
                                          onChange={(e) =>
                                            update(o.id, {
                                              custom_text: e.target.value,
                                            })
                                          }
                                          placeholder="What happened, who was involved, and what should the learner be able to investigate?"
                                        />
                                      </label>
                                      <p>
                                        {bootstrap.capabilities.custom_authoring
                                          ? "Your description will be retained as a draft for validation in the engagement."
                                          : "No model is configured. Your description can be saved as a draft; AI authoring is unavailable."}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              )}
                            </article>
                          ))}
                        </section>
                      ))}
                  </div>
                </div>
              </>
            )}
          </>
        ) : (
          <>
            <h2>Agree scope before company interaction</h2>
            <div className="form-grid">
              <label className="wide">
                Engagement name
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
              </label>
              <fieldset className="wide">
                <legend>Programs and criteria</legend>
                <div className="programs">
                  {bootstrap.programs.map((p) => (
                    <label key={p.id}>
                      <input
                        type="checkbox"
                        disabled={str(p.status).startsWith("BLOCKED")}
                        checked={scope.programs.includes(p.id)}
                        onChange={(e) =>
                          setScope({
                            ...scope,
                            programs: e.target.checked
                              ? [...scope.programs, p.id]
                              : scope.programs.filter((id) => id !== p.id),
                          })
                        }
                      />
                      {str(p.label ?? p.name ?? p.id)}
                      {str(p.status).startsWith("BLOCKED") && (
                        <small>
                          {str(
                            p.reason ??
                              p.blocked_reason ??
                              "Source content unavailable",
                          )}
                        </small>
                      )}
                    </label>
                  ))}
                </div>
                {!bootstrap.programs.length && (
                  <p>No program packs are configured.</p>
                )}
              </fieldset>
              <label>
                Report or engagement type
                <select
                  value={scope.report_type}
                  onChange={(e) =>
                    setScope({ ...scope, report_type: e.target.value })
                  }
                >
                  {[
                    "Type 1",
                    "Type 2",
                    "Internal assessment",
                    "Financial statement audit",
                  ].map((t) => (
                    <option
                      key={t}
                      disabled={
                        t === "Financial statement audit" &&
                        discipline !== "Financial"
                      }
                    >
                      {t}
                    </option>
                  ))}
                </select>
              </label>
              <fieldset>
                <legend>Organization boundaries</legend>
                {(bootstrap.boundaries ?? []).map((b) => (
                  <label key={b.id}>
                    <input
                      type="checkbox"
                      checked={scope.boundaries.includes(b.id)}
                      onChange={(e) =>
                        setScope({
                          ...scope,
                          boundaries: e.target.checked
                            ? [...scope.boundaries, b.id]
                            : scope.boundaries.filter((x) => x !== b.id),
                        })
                      }
                    />
                    {str(b.title)} · {b.id}
                  </label>
                ))}
              </fieldset>

              <label>
                {scope.report_type === "Type 1"
                  ? "Assessment date"
                  : "Period starts"}
                <input
                  type="date"
                  value={scope.period_start}
                  onChange={(e) =>
                    setScope({ ...scope, period_start: e.target.value })
                  }
                />
              </label>
              {scope.report_type !== "Type 1" && (
                <label>
                  Period ends
                  <input
                    type="date"
                    value={scope.period_end}
                    onChange={(e) =>
                      setScope({ ...scope, period_end: e.target.value })
                    }
                  />
                </label>
              )}
              <label>
                Engagement timezone (IANA)
                <input
                  aria-label="Engagement timezone (IANA)"
                  value={str(scope.timezone ?? "UTC")}
                  onChange={(event) =>
                    setScope({ ...scope, timezone: event.target.value })
                  }
                  list="engagement-timezones"
                  required
                />
                <datalist id="engagement-timezones">
                  <option value="UTC" />
                  <option value="America/Denver" />
                  <option value="America/Los_Angeles" />
                  <option value="Europe/Berlin" />
                </datalist>
                <small>
                  Calendar dates and 09:00 fieldwork starts use this timezone,
                  including daylight-saving changes. Explicit timestamp offsets
                  stay unchanged.
                </small>
              </label>
              <label>
                Fieldwork begins
                <input
                  type="date"
                  value={str(scope.fieldwork_start)}
                  onChange={(event) =>
                    setScope({ ...scope, fieldwork_start: event.target.value })
                  }
                />
                <small>
                  Simulation clock starts here, separately from the assessed
                  period. Starting during the period preserves future evidence
                  availability gates.
                </small>
              </label>
              <ScopeDetails
                scope={scope}
                onChange={setScope}
                bootstrap={bootstrap}
              />
            </div>
            <p className="notice">
              The engagement will bind its company version, people, evidence and
              timing before kickoff. Synthetic records and training conclusions
              do not represent an issued audit opinion.
            </p>
            {errors.length > 0 && (
              <ul className="error">
                {errors.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            )}
          </>
        )}
        <footer className="setup-footer">
          <button onClick={step ? () => setStep((n) => n - 1) : onCancel}>
            {step ? "Back" : "Cancel"}
          </button>
          {step < 2 ? (
            <button className="primary" onClick={() => setStep((n) => n + 1)}>
              Continue
            </button>
          ) : (
            <button
              className="primary"
              disabled={
                busy ||
                !!errors.length ||
                !title.trim() ||
                !scope.programs.length
              }
              onClick={() =>
                void onCreate({
                  title,
                  discipline,
                  mode,
                  configuration: serializeConfiguration(
                    mode === "Clean" ? initialConfig() : config,
                  ),
                  scope: {
                    ...scope,
                    period_end:
                      scope.report_type === "Type 1"
                        ? scope.period_start
                        : scope.period_end,
                  },
                })
              }
            >
              {busy ? "Creating engagement…" : "Create & validate engagement"}
            </button>
          )}
        </footer>
      </section>
    </main>
  );
}
