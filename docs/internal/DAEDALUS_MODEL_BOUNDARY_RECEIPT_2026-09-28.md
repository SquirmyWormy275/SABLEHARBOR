# Daedalus local-model boundary receipt — September 28, 2026

This is a bounded model-specific evaluation of the public reference policy
and an isolated local model. It does not claim deployed Daedalus behavior or
close [issue #34](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/34).

An initial authorized-source prompt-injection probe failed: the model obeyed
an instruction inside source text instead of answering the factual question.
The exact failure is retained privately. A revised evaluation prompt passed
the same attack at the same model/seed/temperature. The resulting six-probe
suite passed: one factual answer, three hostile authorized-source instructions,
one denied-source boundary, and one personal-memory boundary. The last two
also verified that protected content was removed **before** the model call.
These are prompt-specific observations, not proof of general semantic safety.

The tested model was Qwen3-4B-Instruct-2507-Q4_K_M, GGUF SHA-256
`8cdb57cbb880d313736a9bc4e3d3d2485f145b5e19cf33783746e753e82641fc`,
served locally by llama.cpp build 10938. Seed was 42, temperature 0 and
the output cap 160 tokens. The private Control repository retains the exact
fixture and full request/response receipts at
`docs/evidence/daedalus-model-boundary-2026-09-28/`, accepted through private
[PR #6](https://github.com/SquirmyWormy275/SABLEHARBOR-ALEXANDRIA-CONTROL/pull/6)
at commit `f85537ae31d81212ef14645cc32146e546217bf8`:

| Private item | SHA-256 |
| --- | --- |
| `EXACT_REPLAY.json` | `ad3ba99b229d2c51f67df4e428fad36b776a15b85932ea7b5974c4daff59a933` |
| `FIXTURES.json` | `a44099b03addecd97def172a13a7e169ebf3ec1ff370726d510a314f844a68de` |
| `SIX_PROBES.json` | `653c6b2bc38319f49ddcc8d0c45e3db04fae2c8eef32d48f5cfda4b48cff6790` |

The public `enterprise.runtime.model_boundary_eval` runner accepts those
private fixtures, applies `security.authorize` to each source before the model
call, rejects a nonlocal endpoint and writes its full receipt outside this
repository. Its ordinary tests use open regression fixtures, not hidden
evaluation answers. The local run and the focused authorization/evaluator
tests passed on this branch. A full Daedalus service integration and broader indirect
disclosure, inference and provider testing remain issue #34 work.
