
# Meeting Copilot — Gold Labeling Guide

## 1. Purpose

This guide defines how meeting transcripts must be labeled when creating gold datasets.

The goal is to ensure that different annotators label the same conversation consistently.

Gold labels represent what was actually communicated in the meeting, not what an annotator thinks participants should do.

Follow these rules consistently. When the transcript does not provide enough information, preserve the uncertainty instead of guessing.

---

## 2. Action Items

An action item represents a task that someone has explicitly committed to completing or that the meeting has identified as a proposed task.

Each action item should have:

- `gold_id`: Unique identifier within the meeting.
- `title`: Short description of the task.
- `owner`: Responsible person, or null if unknown.
- `deadline`: Explicit or contextually resolved date, or null.
- `status`: committed or proposed.
- `turns`: Transcript turn indexes supporting the item.
- `tags`: Optional labels for difficult cases.

### 2.1 Explicit commitment

When a participant explicitly commits to completing a task, label it as `committed`.

The speaker is the owner unless the conversation explicitly assigns responsibility to someone else.

Examples:

| Transcript | Label |
|---|---|
| Priya: "I'll send the report by Friday." | committed, owner = Priya |
| Sam: "I'll handle the deployment." | committed, owner = Sam |
| Dan: "I'll review the document tomorrow." | committed, owner = Dan |

### 2.2 Request followed by acceptance

A request alone is not a commitment. However, an explicit acceptance creates a commitment.

The person accepting the request becomes the owner.

Examples:

| Transcript | Label |
|---|---|
| Priya: "Can you send the report?" Sam: "Sure." | committed, owner = Sam |
| Dan: "Could you check the API?" Priya: "Yes, I'll do it." | committed, owner = Priya |
| Sam: "Can someone review this?" Dan: "I'll take it." | committed, owner = Dan |

Do not assign ownership to the person making the request.

### 2.3 Suggestions without commitment

A general suggestion or recommendation is `proposed`, not `committed`.

If nobody accepts responsibility, owner must be null.

Examples:

| Transcript | Label |
|---|---|
| "Someone should check legal." | proposed, owner = null |
| "We should look into caching." | proposed, owner = null |
| "It would be good to update the documentation." | proposed, owner = null |

Do not convert suggestions into commitments simply because they sound actionable.

### 2.4 Requests without acceptance

An unanswered request does not establish a commitment.

Examples:

| Transcript | Label |
|---|---|
| "Can someone update the dashboard?" | proposed, owner = null |
| "Could you investigate the timeout issue?" (no response) | proposed, owner = null |
| "Who can prepare the presentation?" (no volunteer) | proposed, owner = null |

If someone later accepts the request, label the resulting commitment instead.

---

## 3. Ownership Rules

### 3.1 Speaker ownership

When a participant says "I'll", "I can", or otherwise explicitly commits, assign ownership to that speaker.

Examples:

- Priya: "I'll prepare the slides." → owner = Priya
- Sam: "I can investigate this." → owner = Sam
- Dan: "Leave it to me." → owner = Dan

### 3.2 Explicit reassignment

When responsibility is reassigned during the conversation, keep one final action item with the latest confirmed owner.

Earlier versions are superseded and must not be labeled as separate active action items.

Examples:

| Transcript | Final label |
|---|---|
| Priya: "I'll do it. Actually Sam, you do it." | One item, owner = Sam |
| Dan: "I'll handle deployment." Priya: "Sam should take that instead." Sam: "Okay." | One item, owner = Sam |
| Sam: "I'll review it." Later: "Actually, Priya will handle the review." Priya: "Agreed." | One item, owner = Priya |

Use the turns containing the original commitment and the reassignment as evidence where relevant.

### 3.3 Ambiguous ownership

When multiple people independently claim the same task and the conversation does not establish a single responsible person, assign null ownership.

Add the `ambiguous_owner` tag.

Examples:

- Priya: "I'll take it." Sam: "I'll take it too." → owner = null
- Dan: "I can handle it." Priya: "No, I'll do it." (no resolution) → owner = null
- Sam: "Either Priya or I can take this." → owner = null

Do not choose an owner based on speaking order or personal assumptions.

---

## 4. Deadline Rules

### 4.1 Explicit deadlines

Record deadlines when a participant provides a clear date or time.

Examples:

- "I'll send it on March 14." → deadline = 2025-03-14 (if the meeting year is 2025).
- "Finish this by Friday." → resolve Friday using the meeting date.
- "We need the report before the end of the month." → resolve to the last calendar day of that month if the intended deadline is clear.

If the date cannot be determined reliably, leave deadline null.

### 4.2 Relative deadlines

Relative expressions must be resolved using the meeting date.

Examples:

- "Tomorrow" → meeting date + 1 day.
- "Next Monday" → the following Monday, not automatically the nearest Monday.
- "In two weeks" → meeting date + 14 days.

If the expression is ambiguous, leave deadline null and use the appropriate uncertainty tag.

### 4.3 Deadline revisions

When a deadline changes, retain only the final agreed deadline.

Examples:

| Transcript | Final deadline |
|---|---|
| "Friday... no, make it Monday." | Monday |
| "Let's finish by the 15th. Actually, the 18th works better." | 18th |
| "Try to finish Friday." Later: "Monday is fine." | Monday |

Do not create separate action items for deadline revisions.

### 4.4 Missing deadlines

An action item without a stated or reliably resolved deadline must have:

- `deadline = null`
- `tags` containing `no_deadline`

Never invent deadlines based on typical project timelines.

---

## 5. Conditional Commitments

A conditional commitment is still a commitment when the participant explicitly agrees to perform the task once a condition is satisfied.

Record the condition separately.

Examples:

| Transcript | Label |
|---|---|
| "I'll deploy if Dan approves." | committed, owner = speaker, condition = Dan's approval |
| "I'll publish it once legal signs off." | committed, owner = speaker, condition = legal approval |
| "We can release this if testing passes." | proposed, owner = null, unless someone explicitly commits |

The condition must not be silently removed.

Use the `conditional` tag when applicable.

---

## 6. Follow-ups

A follow-up records a topic that needs to be revisited, checked, or discussed later.

A follow-up is not automatically an action item.

When nobody is assigned responsibility for a general follow-up, label it as a follow-up rather than inventing an owner.

Examples:

- "Let's follow up next week." → follow-up
- "We should revisit the pricing discussion Thursday." → follow-up
- "Let's check the legal position in our next meeting." → follow-up

If a participant explicitly commits to performing a specific task related to the follow-up, label that task separately as an action item.

Example:

- "I'll contact legal and we'll follow up next week." → action item: contact legal; follow-up: revisit the topic next week.

---

## 7. Decisions

A decision represents a choice or conclusion agreed upon during the meeting.

A decision does not require a formal vote or an explicit statement that everyone agrees.

A clear proposal followed by no objection and a conversational transition to the next topic can count as a decision.

Examples:

- "Let's go with Postgres." (nobody objects) → decision
- "We'll use Redis for caching." (team moves forward) → decision
- "Let's postpone the release until Monday." (accepted by the group) → decision

Do not label an unaccepted suggestion as a decision.

Examples:

- "Maybe we should use PostgreSQL." → not necessarily a decision
- "I think Redis could work." → not necessarily a decision
- "What if we postpone the release?" → not necessarily a decision

Look for acceptance, confirmation, or clear conversational adoption.

---

## 8. Open Questions

An open question is a substantive question raised during the meeting that remains unanswered.

It should represent an unresolved information need, not every sentence ending with a question mark.

### 8.1 Unanswered questions

Examples:

- "What's the budget?" (never answered) → open question, answered = false
- "Who owns the refund policy?" (no response) → open question, answered = false
- "When will the vendor confirm?" (no answer) → open question, answered = false

### 8.2 Answered questions

A question is considered answered when a direct, sufficiently relevant answer is provided within approximately 10 subsequent transcript turns.

Examples:

- Priya: "What's the budget?" Sam: "It's ₹50,000." → answered
- Dan: "Who owns the API?" Priya: "Sam owns it." → answered
- Sam: "When is the release?" Dan: "Next Friday." → answered

The answer must actually resolve the question. A vague acknowledgment such as "We'll see" does not count as an answer.

### 8.3 Explicit deferrals

An explicit deferral is different from an unanswered question.

Examples:

- "We don't know yet. We'll find out Thursday."
- "Let's confirm this with finance on Monday."
- "The vendor will give us an answer next week."

Label the question as answered = false, and create a follow-up for the promised future resolution.

Do not treat an explicit deferral as a final answer or create an unresolved question that ignores the agreed follow-up.

The follow-up should capture what needs to be checked and when, if a date is available.

---

## 9. Questions That Should Not Be Labeled

Do not label conversational, rhetorical, or technical communication questions as open questions.

Examples:

- "Can you hear me?"
- "Is my screen visible?"
- "Does everyone understand?"
- "Are we good to proceed?" (when used as a conversational transition and not an unresolved information need)

A question must represent a substantive information need to qualify.

---

## 10. Multiple Tasks in One Sentence

Use one action item per independently executable task.

If a sentence contains multiple distinct tasks, split them into separate action items, even when they share an owner or deadline.

Examples:

**Example 1**

"I'll update the dashboard and send the report."

Label:
- Action item 1: Update the dashboard.
- Action item 2: Send the report.

**Example 2**

"Sam will review the API, update the documentation, and notify the client."

Label:
- Action item 1: Review the API.
- Action item 2: Update the documentation.
- Action item 3: Notify the client.

All three have Sam as owner.

**Example 3**

"I'll test the API and fix any failing tests."

Label:
- One action item: Test the API and fix failing tests.

These are treated as one task because fixing failing tests is part of completing the testing activity.

Do not split a task into artificial subtasks unless each part can be independently assigned, tracked, or completed.

---

## 11. Retractions and Revisions

When a commitment is explicitly withdrawn, do not keep it as an active commitment.

Examples:

- "I'll send the report. Actually, forget it; we don't need it." → retracted, not active
- "We should build this. Actually, let's not pursue it." → proposed item withdrawn
- "I'll handle deployment. Sam will take it instead." → final owner Sam

Use the `retraction` or `revision` tag where applicable.

Do not silently discard important changes in responsibility or scope.

---

## 12. Difficult Cases and Tags

Tags provide additional information for evaluating extraction performance.

Use tags only when they describe a meaningful property of the example.

| Tag | Meaning |
|---|---|
| `retraction` | Previously stated task or commitment withdrawn |
| `revision` | Task, deadline, or ownership revised |
| `asr_error` | Speech recognition error affects interpretation |
| `no_owner` | No responsible person established |
| `ambiguous_owner` | Multiple possible owners remain |
| `conditional` | Commitment depends on a condition |
| `relative_date` | Deadline requires relative date resolution |
| `no_deadline` | No deadline established |
| `unanswered` | Substantive question remains unanswered |
| `deferred` | Resolution explicitly postponed |
| `proposed` | Task suggested without commitment |

Tags supplement the main label. They do not replace fields such as owner, deadline, or status.

---

## 13. Evidence and Annotation Quality

Every gold item must reference at least one supporting transcript turn.

Gold labels use turn indexes, not manually written evidence quotations.

Rules:

1. Use the actual transcript turn indexes.
2. Include the turn containing the commitment, question, decision, or follow-up.
3. Include additional turns when needed to establish acceptance, reassignment, correction, or resolution.
4. Do not reference nonexistent turns.
5. Do not infer information from outside the transcript unless explicitly allowed by the dataset specification.

Examples:

- A direct commitment may need one turn.
- A request followed by acceptance should reference both turns.
- A revised deadline should reference the original and correction turns.
- An answered question should reference both the question and answer turns.

The gold dataset must describe what happened in the conversation, not what would have been reasonable to happen.

---

## 14. Final Annotation Checklist

Before accepting a gold file, verify:

- [ ] Every action item represents an actionable task.
- [ ] Each independent task has its own item.
- [ ] Commitments and proposals are distinguished correctly.
- [ ] Owners are explicitly supported by the transcript.
- [ ] Ambiguous ownership is represented as null.
- [ ] Deadlines are resolved using the meeting date.
- [ ] Deadline revisions retain the final deadline.
- [ ] Conditional commitments retain their conditions.
- [ ] Follow-ups are not incorrectly converted into action items.
- [ ] Decisions have evidence of acceptance or adoption.
- [ ] Open questions represent substantive information needs.
- [ ] Answered questions are marked correctly.
- [ ] Explicit deferrals have corresponding follow-ups.
- [ ] Every item has valid supporting turn indexes.
- [ ] Gold IDs are unique within the meeting.

When uncertain, prefer null or an explicit uncertainty tag over an unsupported assumption.
