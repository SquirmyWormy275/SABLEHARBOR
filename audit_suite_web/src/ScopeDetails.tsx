import { useState } from "react";
import type { Bootstrap, Scope } from "./api";
import { human, str } from "./api";
type Account = {
  id: string;
  name: string;
  assertions: string[];
  risk_rationale: string;
  planned_procedures: string;
};
const assertions = [
  "existence_occurrence",
  "completeness",
  "valuation_allocation",
  "rights_obligations",
  "presentation_disclosure",
];
export default function ScopeDetails({
  scope,
  onChange,
  bootstrap,
}: {
  scope: Scope;
  onChange: (s: Scope) => void;
  bootstrap: Bootstrap;
}) {
  const [choice, setChoice] = useState(""),
    [query, setQuery] = useState(""),
    [ismQuery, setIsmQuery] = useState("");
  const accounts = Array.isArray(scope.accounts)
    ? (scope.accounts as Account[])
    : [];
  const controls = Array.isArray(scope.control_ids)
    ? (scope.control_ids as string[])
    : [];
  const field = (key: string, label: string, multiline = false) => (
    <label className={multiline ? "wide" : ""}>
      {label}
      {multiline ? (
        <textarea
          required
          value={String(scope[key] ?? "")}
          onChange={(e) => onChange({ ...scope, [key]: e.target.value })}
        />
      ) : (
        <input
          required
          value={String(scope[key] ?? "")}
          onChange={(e) => onChange({ ...scope, [key]: e.target.value })}
        />
      )}
    </label>
  );
  function update(id: string, patch: Partial<Account>) {
    onChange({
      ...scope,
      accounts: accounts.map((a) => (a.id === id ? { ...a, ...patch } : a)),
    });
  }
  return (
    <>
      {!scope.programs.includes("SOC1") &&
        !scope.programs.includes("IRAP") &&
        !scope.programs.includes("FINANCIAL") && (
          <details className="wide scoped-program">
            <summary>Optional native control focus</summary>
            <p>
              Leave this empty to include all projected controls. An explicit
              subset limits the training engagement and does not represent
              full-framework assessment coverage.
            </p>
            <label>
              Find controls
              <input
                type="search"
                value={query}
                onChange={(v) => setQuery(v.target.value)}
              />
            </label>
            <fieldset className="control-choices">
              <legend>Selected control subset ({controls.length})</legend>
              {bootstrap.controls
                .filter((c) =>
                  (c.id + " " + str(c.title))
                    .toLowerCase()
                    .includes(query.toLowerCase()),
                )
                .map((c) => (
                  <label key={c.id}>
                    <input
                      type="checkbox"
                      checked={controls.includes(c.id)}
                      onChange={(v) =>
                        onChange({
                          ...scope,
                          control_ids: v.target.checked
                            ? [...controls, c.id]
                            : controls.filter((x) => x !== c.id),
                        })
                      }
                    />
                    {c.id} · {str(c.title)}
                  </label>
                ))}
            </fieldset>
          </details>
        )}
      {scope.programs.includes("IRAP") && (
        <section className="wide scoped-program">
          <h3>IRAP / ISM · scoped non-classified requirements</h3>
          <p>
            {bootstrap.ism_catalog?.attribution} ·{" "}
            {bootstrap.ism_catalog?.license} · {bootstrap.ism_catalog?.version}.
            This training assessment is not ASD certification. Supporting CCF
            controls are not asserted equivalent to selected ISM requirements.
          </p>
          {bootstrap.ism_catalog?.reason && (
            <p role="alert">{bootstrap.ism_catalog.reason}</p>
          )}
          <label>
            Classification
            <select
              required
              value={str(scope.ism_classification)}
              onChange={(v) =>
                onChange({ ...scope, ism_classification: v.target.value })
              }
            >
              <option value="">Choose supported classification</option>
              <option value="NON_CLASSIFIED">Non-classified</option>
            </select>
          </label>
          {field(
            "ism_system_description",
            "System and assessment boundary",
            true,
          )}
          {field(
            "ism_tailoring_rationale",
            "Requirement applicability and tailoring rationale",
            true,
          )}
          <label>
            Search exact publisher requirements
            <input
              type="search"
              value={ismQuery}
              onChange={(v) => setIsmQuery(v.target.value)}
            />
          </label>
          <fieldset className="control-choices">
            <legend>Explicit ISM requirement scope</legend>
            {(bootstrap.ism_catalog?.requirements ?? [])
              .filter((r) =>
                (r.id + " " + str(r.title) + " " + str(r.statement))
                  .toLowerCase()
                  .includes(ismQuery.toLowerCase()),
              )
              .map((r) => {
                const ids = (scope.ism_requirement_ids ?? []) as string[];
                return (
                  <label key={r.id}>
                    <input
                      type="checkbox"
                      checked={ids.includes(r.id)}
                      onChange={(v) =>
                        onChange({
                          ...scope,
                          ism_requirement_ids: v.target.checked
                            ? [...ids, r.id]
                            : ids.filter((x) => x !== r.id),
                        })
                      }
                    />
                    {r.id} · {str(r.title)}
                    <small>{str(r.statement)}</small>
                  </label>
                );
              })}
          </fieldset>
          <fieldset className="control-choices">
            <legend>
              Supporting native controls · explicit selection, no accepted
              mapping
            </legend>
            {bootstrap.controls.map((c) => (
              <label key={c.id}>
                <input
                  type="checkbox"
                  checked={controls.includes(c.id)}
                  onChange={(v) =>
                    onChange({
                      ...scope,
                      control_ids: v.target.checked
                        ? [...controls, c.id]
                        : controls.filter((x) => x !== c.id),
                    })
                  }
                />
                {c.id} · {str(c.title)}
              </label>
            ))}
          </fieldset>
        </section>
      )}
      {scope.programs.includes("C5") && (
        <section className="wide scoped-program">
          <h3>C5 2026 transition</h3>
          <p>
            The installed source is C5 2026 v1.0.1. A Type 2 period spanning 1
            June 2027 requires the 2020 edition, which is unavailable here.
            Choose a supported period explicitly; the same dates apply to this
            entire engagement.
          </p>
          <label className="check">
            <input
              type="checkbox"
              checked={scope.c5_early_adoption === true}
              onChange={(e) =>
                onChange({ ...scope, c5_early_adoption: e.target.checked })
              }
            />
            Use C5 2026 as an early adoption assessment before 1 June 2027
          </label>
          <button
            type="button"
            onClick={() =>
              onChange({
                ...scope,
                period_start: "2027-06-01",
                period_end:
                  scope.report_type === "Type 1" ? "2027-06-01" : "2027-12-31",
              })
            }
          >
            Set this engagement to the June–December 2027 C5 period
          </button>
        </section>
      )}
      {scope.programs.includes("SOC1") && (
        <section className="wide scoped-program">
          <h3>SOC 1 · define the service and objectives</h3>
          {field(
            "service_description",
            "Service and processing boundary",
            true,
          )}
          {field(
            "user_entity_financial_reporting",
            "Effect on user entities’ financial reporting",
            true,
          )}
          <label>
            Service control objectives · one per line
            <textarea
              required
              value={
                Array.isArray(scope.service_control_objectives)
                  ? scope.service_control_objectives.join("\n")
                  : ""
              }
              onChange={(e) =>
                onChange({
                  ...scope,
                  service_control_objectives: e.target.value.split("\n"),
                })
              }
            />
          </label>
          <label>
            Find relevant controls
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <fieldset className="control-choices">
            <legend>
              Select the controls that support these objectives (
              {controls.length})
            </legend>
            {bootstrap.controls
              .filter((c) =>
                (c.id + " " + str(c.title))
                  .toLowerCase()
                  .includes(query.toLowerCase()),
              )
              .map((c) => (
                <label key={c.id}>
                  <input
                    type="checkbox"
                    checked={controls.includes(c.id)}
                    onChange={(e) =>
                      onChange({
                        ...scope,
                        control_ids: e.target.checked
                          ? [...controls, c.id]
                          : controls.filter((x) => x !== c.id),
                      })
                    }
                  />
                  {c.id} · {str(c.title)}
                </label>
              ))}
          </fieldset>
        </section>
      )}
      {(scope.programs.includes("FINANCIAL") ||
        scope.report_type === "Financial statement audit") && (
        <section className="wide scoped-program">
          <h3>Financial statements · account and assertion scope</h3>
          <p>
            Choose the source model explicitly. Assertion vocabulary does not
            choose a jurisdiction or audit methodology.
          </p>
          {field("reporting_basis", "Financial reporting basis")}
          {field(
            "financial_audit_jurisdiction",
            "Audit jurisdiction and methodology",
          )}
          {field(
            "materiality_rationale",
            "Materiality and planning rationale",
            true,
          )}
          <div className="actions">
            <label>
              Source-model account
              <select
                value={choice}
                onChange={(e) => setChoice(e.target.value)}
              >
                <option value="">Select an account…</option>
                {bootstrap.financial_accounts
                  ?.filter((a) => !accounts.some((x) => x.id === a.id))
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.id} · {str(a.name)}
                    </option>
                  ))}
              </select>
            </label>
            <button
              type="button"
              disabled={!choice}
              onClick={() => {
                const row = bootstrap.financial_accounts?.find(
                  (a) => a.id === choice,
                );
                if (row)
                  onChange({
                    ...scope,
                    accounts: [
                      ...accounts,
                      {
                        id: row.id,
                        name: str(row.name),
                        assertions: [],
                        risk_rationale: "",
                        planned_procedures: "",
                      },
                    ],
                  });
                setChoice("");
              }}
            >
              Add account
            </button>
          </div>
          {accounts.map((a) => (
            <fieldset key={a.id}>
              <legend>
                {a.id} · {a.name}
              </legend>
              <div className="assertion-choices">
                {assertions.map((assertion) => (
                  <label key={assertion}>
                    <input
                      type="checkbox"
                      checked={a.assertions.includes(assertion)}
                      onChange={(e) =>
                        update(a.id, {
                          assertions: e.target.checked
                            ? [...a.assertions, assertion]
                            : a.assertions.filter((x) => x !== assertion),
                        })
                      }
                    />
                    {human(assertion)}
                  </label>
                ))}
              </div>
              <label>
                Account-specific risk rationale
                <textarea
                  required
                  value={a.risk_rationale}
                  onChange={(e) =>
                    update(a.id, { risk_rationale: e.target.value })
                  }
                />
              </label>
              <label>
                Planned procedures, timing and extent
                <textarea
                  required
                  value={a.planned_procedures}
                  onChange={(e) =>
                    update(a.id, { planned_procedures: e.target.value })
                  }
                />
              </label>
              <button
                type="button"
                onClick={() =>
                  onChange({
                    ...scope,
                    accounts: accounts.filter((x) => x.id !== a.id),
                  })
                }
              >
                Remove account
              </button>
            </fieldset>
          ))}
        </section>
      )}
    </>
  );
}
