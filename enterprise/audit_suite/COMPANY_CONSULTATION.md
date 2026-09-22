# Attributed company consultation and correction requests

Company-source meetings support an optional, explicit consultation link on the existing
`meeting.message` command. This records a learner-requested referral or correction request.
It does not claim the original company contact initiated the consultation. The responding
company person's text is produced only by the existing configured persona pipeline.

The optional `consultation` payload has exactly these fields:

```json
{
  "kind": "REFERRAL",
  "question_ref": {"meeting_id": "MTG-origin", "message_id": "MSG-question", "sha256": "…"},
  "response_ref": null
}
```

`kind` is `REFERRAL` or `CORRECTION_REQUEST`. A correction request requires an exact prior
company response reference, with the same three fields. The selected response must belong
to the selected question's exchange. Referrals require a different current scoped company
contact. The target remains the existing command's `meeting_id`; callers cannot supply a
company speaker, company answer or reply relationship. A meeting's control-specific route
must still contain the consulted contact. Proposed contact assignments do not create new
corporate authority or employment facts.

`company_consultation_inputs` in the current authorized engagement projection supplies
server-generated message digests. It contains `status` and `questions`; each question has
`ref`, `meeting_title`, `person_id`, `content`, `simulated_at`, and `responses`. Each response
has its own `ref`, `person_id`, `content` and `simulated_at`. The UI must use these exact pins,
clear selections on actor/context changes, and never reconstruct digests or substitute a
later message. Unavailable, malformed, inactive or oversized contexts return no choices.
The bound is 2,000 messages and 500 questions.

For consultation, original company support is explicitly selected through the existing
one-to-four `source_records` contract. Omission means `SUPPORT_NOT_SUPPLIED`: it disables
implicit source sampling for this request. It does not establish that records do not
exist. Source access remains the intersection of the auditor's current engagement grants
and the responding person's registered source systems. Native identity, physical store,
portfolio alias/registry pin, version, SHA, dates, qualifiers and excerpt-locator hashes
are retained in a metadata-only source manifest. No source bytes are automatically retained
as audit evidence, and the consultation does not create access grants.

The provider returns an explicit `consultation_relation`: `ANSWERS`, `CLARIFIES`,
`CORRECTS` or `CANNOT_ESTABLISH`. `CORRECTS` requires the pinned prior company response.
This is an attributed company statement, not verified correctness, automatic acceptance,
source supersession or an audit conclusion. Original messages remain unchanged. Historical
question/response text enters model context with explicit learner/company attribution and
statement-only authority. Consultation cannot execute proposed PBC actions or start another
reply job automatically.

Actor access, engagement revision, scope, company binding, contact route and exact selected
source authority are checked before the reply, immediately after it before note extraction,
after note extraction and before persistence. Source revocation or context change prevents
the reply from being saved. The existing note extraction remains a separate attributed note,
not a replacement for original messages.

Durable jobs use the existing `meeting.message` kind and exact command replay/CAS contract.
A future scheduled meeting returns `CONSULTATION_DELAYED` without calling a model. Source
failures remain generic `SOURCE_CONTEXT_UNAVAILABLE`, without disclosing whether hidden
records exist. Pending, failed, interrupted and conflicted jobs remain visible through the
existing job history. Changing the simulated clock changes engagement revision, so an
operator must inspect the failed request and explicitly submit a new command. No automatic
retry, role expansion, staff absence claim or successful consultation is invented.

Legacy meeting messages without consultation are unchanged. Tests use disposable company
sources and a stub provider only; they verify original preservation, exact pins, typed reply
relations, replay, future denial, missing support, source/actor revocation, revision races,
projection failure containment and compatibility with ordinary meetings/jobs/inference.
No live model invocation or institutional/professional acceptance is claimed by these tests.
