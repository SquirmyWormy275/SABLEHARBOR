# V12 selected-transfer portfolio preparation

This branch prepares a partial fictional 2027 source roster and candidate routing
extension for one SEC001 selected synthetic transfer source. It starts from main
`8ca005971209111260b63bb682bbf865053175c9`. The new source's isolated run
is a proposal, and its main-local independent review is still pending. The V12
portfolio and candidate builders therefore raise
`SEC001 accepted main source/review pins pending` before writing any output.

The reviewed V11 portfolio and A/B candidate bytes remain exact inputs. V11 has
32 cohorts, 729 native business versions, 33 scenario source pins per side,
46 total components per side and 285 aliases. The planned SEC001 addition has
26 native versions (10 Clean, 16 Messy) and five systems per branch. Once the
source's main-local run and independent review are accepted, V12 should have
33 cohorts, 755 versions, 34 pins, 47 components and 290 aliases per side.
The candidate builder compares the entire V11 source, manifest and pin prefix.

The source contains one synthetic, non-PHI transfer custody fixture per branch.
The Clean selected reconciliation is fictional. Messy retains a blocked
wrong-endpoint attempt, corrected false completion and open historical exception.
The exact `SH-SEC-001` authored clause remains unsupported, and its P1 task is
`NOT_STARTED`/`NOT_RUN`. There is no real network transmission, deployed channel
or endpoint, independent approval, enterprise transfer standard, source-complete
population, grant, collection, audit task credit, Key or grade.

Before enabling V12, record the accepted main source review SHA and verdict,
integration commit, and exact main run manifest, receipt, database and tracked
module SHA-256 values in the V12 portfolio module. Confirm the review pins those
same bytes, the source verifier passes, and the frozen 538-file P1 inventory is
unchanged. Then create fresh private V12 report and A/B candidate outputs and
seek separate independent review. Isolated-source hashes or an unreviewed main
run do not satisfy this gate.
