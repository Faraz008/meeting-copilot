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
