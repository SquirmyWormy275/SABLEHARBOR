# Assumption register

The machine-readable source is `config/finance/assumptions/*.yml`. Values are loaded and validated by the application and later exported to SQL and Excel.

| ID | Assumption | State | Base | Sensitivity | Review owner |
|---|---|---|---|---|---|
| FIN-BASE-001 | Quantitative architecture | MODEL_PROPOSED | Alternative B / synthetic CoreCo scenario calibration | High | Finance Planning; Orientation canon review |

All numeric assumptions produce synthetic scenario/calibration records. They do not represent
observed company results or audited books.
