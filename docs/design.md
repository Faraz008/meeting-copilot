# Design: Building a Meeting Copilot That Doesn't Trust Its Own LLM

*Architecture decisions, guardrails, experiments, and lessons from building an evidence-grounded meeting copilot.*

## 1. The problem: extraction is easy until it isn't

Meeting action-item extraction looks deceptively simple. Give an LLM a transcript and ask it to return action items, owners, deadlines, decisions, and unresolved questions. On a clean transcript, this can work surprisingly well.

The problems appear when conversations become messy. Someone proposes an action that is never agreed upon. An owner is mentioned without accepting responsibility. A deadline is expressed as "next Friday." An action is revised later in the meeting. A question is answered several minutes after it was raised.

An LLM can produce convincing JSON while getting these details wrong. The output may be structurally valid and confidently worded, yet invent an owner, misinterpret a deadline, or extract a proposal as a commitment.

I wanted to build something that could extract useful meeting information without treating an LLM response as ground truth. The design therefore separates language understanding from deterministic application logic, validates evidence against the transcript, restricts reconciliation, and evaluates the pipeline against annotated meetings instead of relying on a few successful examples.

## 2. Data model design

### 2.1 Stable IDs

IDs are generated from the meeting ID and the position of the evidence in the transcript, rather than from LLM-generated wording.

This ensures that the same extracted item receives the same ID across repeated runs, provided its meeting and transcript position remain unchanged.

Stable IDs are important for idempotent operations in later integration phases. For example, pushing the same action item to an external task manager should not create duplicate tasks.

### 2.2 Raw and resolved fields

Action items maintain separate raw and resolved fields for owners and deadlines:

- `owner_raw`: The owner name or reference reported by the LLM.
- `owner`: The owner resolved by deterministic application logic.
- `deadline_raw`: The deadline expression reported by the LLM.
- `deadline`: The normalized Python date resolved by deterministic application logic.

The LLM is responsible for extracting what was said. Deterministic code is responsible for resolving identities and dates.

This separation prevents the application from treating an LLM interpretation as a verified value.

### 2.3 Evidence requirements

Every extracted action item, decision, open question, and follow-up must contain at least one evidence reference.

The `evidence` field uses Pydantic's `min_length=1` constraint.

An item without supporting transcript evidence cannot pass model validation. This guardrail is enforced at the data-model level rather than relying only on LLM instructions or prompt engineering.

Evidence contains:

- `turn_idx`: The transcript turn containing the supporting statement.
- `quote`: A verbatim quotation from the transcript.

### 2.4 Evidence grounding

Extracted evidence is checked against the original transcript before an item is accepted.

Grounding first checks the predicted turn, then the immediately preceding and following turns to account for off-by-one errors in LLM-generated turn references.

Evidence that fails grounding is removed from the item. If no evidence survives grounding, the item is rejected.

Rejected items are counted when calculating the hallucination rate.

Short quotes require a whole-word match rather than fuzzy matching. This prevents short strings from receiving false matches inside longer words.

### 2.5 Deadline validation

The `deadline_raw` expression must appear near the item's supporting evidence in the transcript.

If the deadline expression cannot be found near the evidence, it is removed and a validation note is recorded.

The item subsequently receives the `no_deadline` flag when no valid deadline remains.

### 2.6 Superseded items

Superseded action items are retained rather than deleted.

When an existing action item is replaced or invalidated by a later discussion, its status becomes `superseded`, and `superseded_by` can reference the replacement item's ID.

This preserves the history of decisions and commitments instead of losing previously extracted information.

## 3. Deterministic deadline resolution

Deadline expressions are normalized using deterministic rules based on the meeting date.

The following conventions are used:

- A bare weekday means its next occurrence after the meeting date. If the meeting falls on that weekday, the result is ambiguous because it could mean today or the following week.
- `this <weekday>` means that weekday in the current calendar week (Monday to Sunday). If it has already passed, it rolls forward to the following week.
- `next <weekday>` means that weekday in the next calendar week. If the nearest upcoming occurrence differs, the result is ambiguous. The next week's date is used as the primary date, and both dates are included in `options`.
- `end of week` / `EOW` resolves to Friday.
- `EOD` / `COB` resolves to today at 17:00.
- `end of month` resolves to the last calendar day of the month.
- `next week` is ambiguous between Monday and Friday. Friday is used as the primary date.
- `next month` is ambiguous between the first and last day of the next month. The last day is used as the primary date.

Event-relative and vague expressions such as "before the release", "ASAP", "when Dan approves", and "a few days" are unresolvable. They are flagged rather than assigned guessed dates.

`before X` is treated as `X`. Applying a stricter interpretation of "before" is left to human review.

Ambiguous deadlines retain their primary resolved date and receive a flag. This keeps the action item useful while making it clear that human confirmation is required.

Unresolvable deadlines are flagged and are not assigned guessed dates.

The purpose of this design is to make deadline behavior explicit and testable. Date interpretation should not depend on which model happens to be called or whether the provider performs date arithmetic correctly.

## 4. Reconciliation design

### 4.1 Core principle

Pass 2 can only **merge, annotate, or downgrade** items produced by Pass 1. It must never create new items.

Pass 1 is responsible for extracting candidate items from the transcript. Pass 2 reviews those candidates across transcript chunks to reconcile information that may have been missed or contradicted by chunk boundaries.

This restriction ensures that reconciliation cannot introduce entirely new, unsupported action items, decisions, or questions.

### 4.2 Deterministic reconciliation

Merging and supersession of action items are handled by deterministic application logic rather than the LLM.

Code is responsible for:

- Identifying duplicate action items.
- Merging compatible items.
- Preserving stable IDs and evidence references.
- Marking replaced or invalidated items as `superseded`.
- Linking superseded items to their replacements through `superseded_by`, where applicable.

### 4.3 LLM-assisted judgments

The LLM is used only for two reconciliation judgments that cannot be reliably determined through simple deterministic rules:

1. **Question resolution:** Whether an existing open question was answered later in the meeting.
2. **Decision reversal:** Whether a previously recorded decision was explicitly reversed during subsequent discussion.

The LLM does not directly modify the extracted collection or introduce new items. It provides judgments for deterministic application logic to validate and apply.

### 4.4 Evidence-grounded judgments

Every LLM reconciliation judgment must include a supporting quotation grounded in the transcript.

A judgment without valid supporting evidence is ignored.

The application validates the quotation against the original transcript before accepting the judgment. Unsupported or ungrounded judgments must not change an item's status or other resolved fields.

This ensures that Pass 2 can improve consistency across transcript chunks without introducing hallucinated information or overriding previously extracted data without evidence.

### 4.5 Pipeline invariant

The reconciliation pipeline follows these rules:

- Pass 1 extracts candidate items.
- Pass 2 reconciles existing candidates only.
- Deterministic code handles merging, supersession, and state updates.
- LLM judgments are restricted to question resolution and decision reversal.
- Every accepted LLM judgment requires validated transcript evidence.
- Pass 2 cannot increase the number of extracted items by creating new ones.

## 5. Application architecture

### 5.1 Single service layer

The application uses a single service layer (`service.py`) for its core workflows.

The UI, CLI, and API act as thin interfaces over this service rather than implementing their own extraction, validation, reconciliation, or integration logic.

This keeps business logic centralized and ensures that the same operations behave consistently regardless of how they are invoked.

### 5.2 Human approval boundary

Nothing leaves the machine without human approval.

Extraction and processing only write to the local database. External integrations can push only items explicitly marked as `approved`.

Email integration defaults to dry-run mode, generating or previewing the intended output without sending it.

Approval is required before any external write or communication takes place.

### 5.3 Untrusted transcript input

The transcript is treated as untrusted input.

Every string originating from the transcript must be escaped or safely encoded for its destination before being rendered or transmitted.

This applies to HTML, Markdown, Slack messages, email content, and Jira fields.

Transcript content must never be treated as trusted markup, executable instructions, or formatting supplied by the application.

## 6. Integration design

### 6.1 Field ownership

The application and external task managers have separate ownership over different fields.

**Copilot-owned content fields:**

- Title
- Deadline
- Evidence

**Human-owned workflow fields:**

- Notion `Stage`
- Jira status
- Jira assignee after creation

Copilot can create and update its content fields in external systems, but must not overwrite human-owned workflow fields during subsequent updates.

This preserves human control over task execution and workflow management.

### 6.2 External item lifecycle

Copilot never deletes or closes external items.

When an external item no longer has a corresponding active item in the local database, it is reported as an orphan for human review.

The application does not automatically delete, archive, or close such items.

This ensures that external task history and human workflow decisions remain under human control.

## 7. Why deterministic code handles dates and owners

One of the main architectural decisions was to separate extraction from resolution.

The LLM extracts what was actually said. It returns raw fields such as `owner_raw` and `deadline_raw`. Application code then resolves those fields against the meeting roster and meeting date.

For example, if a transcript says:

> "Let's get this done next Friday."

The model should extract the deadline phrase, not calculate a date and silently choose an interpretation. The application resolves the phrase according to documented conventions and records ambiguity where necessary.

The `no_code_dates` ablation did not produce a measurable change in aggregate deadline accuracy in the observed development runs. This does not make deterministic resolution unnecessary. The development set is small, and an ablation can only tell me whether a component changed outcomes on the cases represented in that dataset.

I prefer a tested date resolver with explicit ambiguity handling over relying on a model to perform date arithmetic consistently.

## 8. Why evidence is a correctness boundary

An action item without evidence is difficult to trust or review. Every extracted item therefore needs supporting transcript evidence.

The validator checks the referenced turn and nearby turns to tolerate small turn-index discrepancies. It verifies the quoted text against the transcript, removes invalid evidence, and rejects an item if no valid evidence remains. Rejected outputs still count in the evaluation's hallucination accounting rather than disappearing from the metric.

This creates a boundary between model output and trusted application data:

1. The model proposes an item and evidence.
2. The validator checks the evidence against the transcript.
3. Invalid evidence is removed.
4. An item without remaining evidence is rejected.
5. Valid items continue through resolution and reconciliation.

The grounding ablation was not a dramatic aggregate F1 improvement on this dataset. For Ollama, removing grounding increased the reported ungrounded-output rate from 0% to 3%. The headline action metrics generally remained unchanged.

A validator can still be valuable when a small benchmark doesn't show a large F1 improvement. Its purpose is to enforce a correctness boundary, not simply optimize one metric.

## 9. Why Pass 2 cannot invent items

The pipeline uses a second pass to reconcile information across chunks of a meeting. Without constraints, another LLM pass can introduce additional items while trying to improve the output.

I restricted the second pass to three operations:

- Merge duplicate items.
- Annotate or clarify existing items.
- Downgrade items when their status or interpretation is no longer supported.

It cannot create new action items. This is enforced as a pipeline invariant: the second pass cannot increase the number of items.

The application handles deterministic operations such as deduplication, merging, and supersession. When an action is revised, the old item is retained and marked as superseded, with a link to the replacement. Stable IDs are generated from the meeting and evidence position rather than the wording generated by the model. This makes item identity more reliable across reruns and supports idempotent integrations.

The LLM is used for narrow reconciliation judgments, such as whether a question was answered later or whether a decision was reversed. Those judgments must be grounded in transcript evidence. Unsupported or invalid judgments are ignored.

The `no_pass2` ablation did not show a consistent headline improvement. For some provider runs, unresolved-question recall increased from 50% to 100% without Pass 2, but paired confidence intervals included zero. The evidence is not strong enough to conclude that Pass 2 is harmful.

The design constraint remains useful regardless: reconciliation should be allowed to correct the existing extraction, not expand it without evidence.

## 10. Measurement and evaluation

I created gold annotations for action items, decisions, questions, owners, deadlines, and relevant hard cases. Evaluation includes both title-based and turn-based matching, with error reports that classify misses, false positives, duplicates, incorrect owners, deadline errors, and other failures.

The development experiments use six meetings, while the frozen held-out test uses ten meetings and 23 gold action items. The held-out set was not used for prompt selection or tuning. The final protocol preserves the split and its integrity manifest.

### Run-to-run variation

I also ran repeated Groq experiments to estimate run-to-run variation. Across three runs on the development meetings, Action F1 had a standard deviation of 0.7 percentage points and precision had a standard deviation of 0.8 percentage points.

The corresponding two-standard-deviation estimates were approximately:

- Action F1: 1.4 percentage points.
- Action precision: 1.6 percentage points.

These are preliminary estimates, not universal statistical thresholds. They are useful reminders that small changes in a metric may be ordinary variation.

### F1 is not the entire story

The results showed that headline F1 can hide meaningful trade-offs. In one Ollama v2 comparison, the baseline achieved 95% Action F1 but only 30% fully-correct action recall. The full pipeline had 69% F1 and 100% fully-correct recall, alongside improved owner and deadline accuracy.

A system that produces more partially correct items is not necessarily more useful than one that produces fewer but better-supported items.

### Benchmark limitations

The benchmark is still small and synthetic-heavy. The held-out test contains ten synthetic meetings and no real meetings. Real AMI transcripts were collected for exploration, but they were not part of the scored held-out test.

The results therefore do not establish generalization to naturally occurring workplace conversations. The test set is useful for controlled comparison and regression measurement, but not as a universal estimate of real-world meeting performance.

## 11. What failed

### 11.1 The v2 prompt

I tried stricter prompt instructions to distinguish decisions from ownership clarifications and responsibility statements, and to preserve substantive questions for downstream resolution.

The Groq development result regressed:

| Metric | v1 | v2 |
|---|---:|---:|
| Action F1 | 59% | 52% |
| Action recall | 100% | 70% |
| Fully-correct action recall | 100% | 60% |
| Owner accuracy | 100% | 86% |
| Unresolved-question recall | 100% | 50% |
| Decision F1 | 0% | 0% |

The confidence intervals were wide, so I cannot claim a statistically conclusive regression. However, the observed pattern did not meet my acceptance criteria. I retained v1 rather than promoting v2.

### 11.2 Threshold tuning

I swept the deduplication, supersession, and grounding thresholds individually across three values each. The reported aggregate metrics were identical across tested values.

The experiment provided no evidence that changing the defaults improved performance. I kept the existing thresholds instead of selecting a value based on an unmeasurable difference.

### 11.3 Removing completed-item filtering

The completed-item filtering experiment also produced identical aggregate metrics. The development annotations did not contain the intended `past_tense_negative` cases, so the experiment could not meaningfully test the hypothesis.

The lesson was to check whether the benchmark actually contains the failure cases an experiment is intended to address.

### 11.4 Removing pipeline components

Removing grounding and code-date handling generally did not change aggregate action metrics in the observed v2 runs. Removing Pass 2 changed unresolved-question recall for some providers, but the confidence intervals were too wide to establish a reliable improvement.

The Ollama baseline also demonstrated that a higher action F1 does not necessarily mean better end-to-end extraction: its full pipeline had lower F1 but much higher fully-correct action recall and owner/deadline accuracy.

No component was removed based only on these small ablation results.

### 11.5 Provider comparisons

The providers behaved differently across the same prompt and pipeline configurations. OpenRouter also had incomplete `s01` runs in several configurations, which prevents a clean comparison with its baseline.

I avoid treating one provider's aggregate score as proof that it is universally better. Complete, same-meeting runs are needed before drawing stronger conclusions.

## 12. From extraction to execution

The copilot does not automatically push every extracted item into external systems. There is an approval boundary between reviewing the meeting output and executing integrations.

Stable IDs support idempotency. Human-owned fields, such as Notion Stage or Jira status after creation, are not overwritten by the copilot. Integration payloads are escaped for their target formats, and external pushes are restricted to approved items. Dry-run behavior is available so execution can be reviewed before it takes effect.

These constraints are part of the design, not optional safeguards added after the extraction logic.

## 13. What I would improve next

The most important next step is evaluation on real meetings. The current synthetic-heavy benchmark is useful for controlled failure cases but does not capture the full variability of workplace speech.

I would also expand the gold set for decisions and no-owner/proposed-action cases, where the development experiments exposed weaknesses. Finally, I would improve provider reliability and operational handling of rate limits and incomplete runs, because a pipeline that cannot finish a meeting consistently is not useful regardless of its extraction metrics.

The central lesson of this project is that an LLM should propose, not certify. The model is responsible for understanding language. The application is responsible for enforcing rules, checking evidence, resolving ambiguity, preserving identity, measuring failures, and deciding when the output is safe to execute.
