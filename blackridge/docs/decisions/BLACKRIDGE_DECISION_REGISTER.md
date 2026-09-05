# Blackridge Implementation Decision Register

| ID | State | Decision | Reason | Reversibility |
|---|---|---|---|---|
| BRG-P001 | PROVISIONAL | USD calendar-year reporting entity | Minimal coherent case perimeter | Configuration change |
| BRG-P002 | PROVISIONAL | Integer cents and quantity thousandths | Exact deterministic arithmetic | Migration |
| BRG-P003 | PROVISIONAL | UUID5 public identities | Stable replay without stored secrets | Namespace migration |
| BRG-P004 | PROVISIONAL | SQLite release database | Zero-configuration participant access | PostgreSQL DDL supplied |
| BRG-P005 | PROVISIONAL | High-volume workbook facts redirect to SQL/CSV | Avoid silent Excel truncation | Workbook profile change |

LOCKED canon values remain controlled by the handoff and accepted Sable Harbor canon. These
implementation decisions do not supersede canon and remain subject to independent review.
