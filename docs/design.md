# Design Doc

## Data Model Design

### Stable IDs

IDs are generated from the meeting ID and the position of the evidence in the transcript, rather than from LLM-generated wording.

This ensures that the same extracted item receives the same ID across repeated runs, provided its meeting and transcript position remain unchanged.

Stable IDs are important for idempotent operations in later integration phases. For example, pushing the same action item to an external task manager should not create duplicate tasks.

### Raw and Resolved Fields

Action items maintain separate raw and resolved fields for owners and deadlines:

- `owner_raw`: The owner name or reference reported by the LLM.
- `owner`: The owner resolved by deterministic application logic.
- `deadline_raw`: The deadline expression reported by the LLM.
- `deadline`: The normalized Python date resolved by deterministic application logic.

The LLM is responsible for extracting what was said. Deterministic code is responsible for resolving identities and dates.

This separation prevents the application from treating an LLM interpretation as a verified value.

### Evidence Requirements

Every extracted action item, decision, open question, and follow-up must contain at least one evidence reference.

The `evidence` field uses Pydantic's `min_length=1` constraint.

An item without supporting transcript evidence cannot pass model validation. This guardrail is enforced at the data-model level rather than relying only on LLM instructions or prompt engineering.

Evidence contains:

- `turn_idx`: The transcript turn containing the supporting statement.
- `quote`: A verbatim quotation from the transcript.

### Evidence Grounding

Extracted evidence is checked against the original transcript before an item is accepted.

Grounding first checks the predicted turn, then the immediately preceding and following turns to account for off-by-one errors in LLM-generated turn references.

Evidence that fails grounding is removed from the item. If no evidence survives grounding, the item is rejected.

Rejected items are counted when calculating the hallucination rate.

Short quotes require a whole-word match rather than fuzzy matching. This prevents short strings from receiving false matches inside longer words.

### Deadline Validation

The `deadline_raw` expression must appear near the item's supporting evidence in the transcript.

If the deadline expression cannot be found near the evidence, it is removed and a validation note is recorded.

The item subsequently receives the `no_deadline` flag when no valid deadline remains.

### Superseded Items

Superseded action items are retained rather than deleted.

When an existing action item is replaced or invalidated by a later discussion, its status becomes `superseded`, and `superseded_by` can reference the replacement item's ID.

This preserves the history of decisions and commitments instead of losing previously extracted information.

### Deadline Resolution Conventions

Deadline expressions are normalized using deterministic rules based on the meeting date.

The following conventions are used:

- A bare weekday means its next occurrence after the meeting date. If the meeting falls on that weekday, the result is ambiguous because it could mean today or the following week.
- `this <wd>` means that weekday in the current calendar week (Monday to Sunday). If it has already passed, it rolls forward to the following week.
- `next <wd>` means that weekday in the next calendar week. If the nearest upcoming occurrence differs, the result is ambiguous. The next week's date is used as the primary date, and both dates are included in `options`.
- `end of week` / `EOW` resolves to Friday.
- `EOD` / `COB` resolves to today at 17:00.
- `end of month` resolves to the last calendar day of the month.
- `next week` is ambiguous between Monday and Friday. Friday is used as the primary date.
- `next month` is ambiguous between the first and last day of the next month. The last day is used as the primary date.

Event-relative and vague expressions such as "before the release", "ASAP", "when Dan approves", and "a few days" are unresolvable. They are flagged rather than assigned guessed dates.

`before X` is treated as `X`. Applying a stricter interpretation of "before" is left to human review.

Ambiguous deadlines retain their primary resolved date and receive a flag. This keeps the action item useful while making it clear that human confirmation is required.

Unresolvable deadlines are flagged and are not assigned guessed dates.

## Reconciliation Design

### Core Principle

Pass 2 can only **merge, annotate, or downgrade** items produced by Pass 1. It must never create new items.

Pass 1 is responsible for extracting candidate items from the transcript. Pass 2 reviews those candidates across transcript chunks to reconcile information that may have been missed or contradicted by chunk boundaries.

This restriction ensures that reconciliation cannot introduce entirely new, unsupported action items, decisions, or questions.

### Deterministic Reconciliation

Merging and supersession of action items are handled by deterministic application logic rather than the LLM.

Code is responsible for:

- Identifying duplicate action items.
- Merging compatible items.
- Preserving stable IDs and evidence references.
- Marking replaced or invalidated items as `superseded`.
- Linking superseded items to their replacements through `superseded_by`, where applicable.

### LLM-Assisted Judgments

The LLM is used only for two reconciliation judgments that cannot be reliably determined through simple deterministic rules:

1. **Question resolution:** Whether an existing open question was answered later in the meeting.
2. **Decision reversal:** Whether a previously recorded decision was explicitly reversed during subsequent discussion.

The LLM does not directly modify the extracted collection or introduce new items. It provides judgments for deterministic application logic to validate and apply.

### Evidence-Grounded Judgments

Every LLM reconciliation judgment must include a supporting quotation grounded in the transcript.

A judgment without valid supporting evidence is ignored.

The application validates the quotation against the original transcript before accepting the judgment. Unsupported or ungrounded judgments must not change an item's status or other resolved fields.

This ensures that Pass 2 can improve consistency across transcript chunks without introducing hallucinated information or overriding previously extracted data without evidence.

### Pipeline Invariant

The reconciliation pipeline follows these rules:

- Pass 1 extracts candidate items.
- Pass 2 reconciles existing candidates only.
- Deterministic code handles merging, supersession, and state updates.
- LLM judgments are restricted to question resolution and decision reversal.
- Every accepted LLM judgment requires validated transcript evidence.
- Pass 2 cannot increase the number of extracted items by creating new ones.

## Application Architecture

### Single Service Layer

The application uses a single service layer (`service.py`) for its core workflows.

The UI, CLI, and API act as thin interfaces over this service rather than implementing their own extraction, validation, reconciliation, or integration logic.

This keeps business logic centralized and ensures that the same operations behave consistently regardless of how they are invoked.

### Human Approval Boundary

Nothing leaves the machine without human approval.

Extraction and processing only write to the local database. External integrations can push only items explicitly marked as `approved`.

Email integration defaults to dry-run mode, generating or previewing the intended output without sending it.

Approval is required before any external write or communication takes place.

### Untrusted Transcript Input

The transcript is treated as untrusted input.

Every string originating from the transcript must be escaped or safely encoded for its destination before being rendered or transmitted.

This applies to HTML, Markdown, Slack messages, email content, and Jira fields.

Transcript content must never be treated as trusted markup, executable instructions, or formatting supplied by the application.

## Integration Design

### Field Ownership

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

### External Item Lifecycle

Copilot never deletes or closes external items.

When an external item no longer has a corresponding active item in the local database, it is reported as an orphan for human review.

The application does not automatically delete, archive, or close such items.

This ensures that external task history and human workflow decisions remain under human control.
