# Meeting Copilot — Product Specification

## Problem

Meeting transcripts contain important action items, decisions, unanswered questions, and follow-ups, but manually identifying and organizing them is time-consuming. Meeting Copilot converts recorded meeting transcripts into structured, evidence-backed outputs so users can understand what was agreed, who is responsible, and what still needs attention.

## Inputs

- VTT transcript files.
- SRT subtitle files.
- TXT files formatted as `Speaker: text`.
- Zoom transcript exports.
- Microsoft Teams transcript exports.
- Meeting date, supplied by the user.
- Meeting timezone, supplied by the user.

## Outputs

The system produces four categories:

- **Action items:** Concrete tasks with an assigned person or role, deadline when available, and status.
- **Decisions:** Choices explicitly accepted by the group.
- **Open questions:** Work-related questions left unanswered.
- **Follow-ups:** Topics or items to revisit, without an assigned owner.

Every extracted item must include:

- **Evidence:** The supporting transcript excerpt and its speaker or timestamp when available.
- **Flags:** Relevant uncertainty or classification indicators, such as missing owner, missing deadline, proposed status, or ambiguous attribution.

### Integrations

The system should support exporting validated action items and follow-ups to external productivity tools.
Planned integrations:

Notion
Jira
Email

Exports should preserve task descriptions, owners, deadlines, evidence and relevant flags.
Integration support may be implemented as a later feature; it is not required for the initial extraction pipeline.

## Non-goals

- No live meeting bot.
- No real-time transcription or processing.
- No multi-language support in v1.
- No calendar scheduling or automatic meeting booking.

## Definitions

### Action item

A specific person or role explicitly takes on, or is explicitly assigned, a concrete future task.

**Test:** Could someone later ask, "Did you do it?"

If not, it is not a committed action item.

### Proposed

A suggestion that has not been committed to.

Example: "We should probably look into X."

Extract it with `status=proposed`. Do not treat it as a committed action item.

### Decision

A stated choice among alternatives that the group accepts.

Example: "Let's go with Postgres."

It is not a decision if someone objects and the disagreement remains unresolved.

### Open question

A question about the work that nobody answers before the meeting ends or the discussion moves to another topic.

Rhetorical and social questions, such as "Can you hear me?", do not count.

### Follow-up

Something to revisit later or a topic for a future meeting, with no specific person assigned to it.

If a person is explicitly assigned a concrete task, classify it as an action item instead.

## Success metrics

Thresholds will be defined in a later project week.

- **Action-item F1:** Measures the balance between precision and recall when extracting action items.
- **Owner accuracy:** Measures whether extracted action items are assigned to the correct person or role.
- **Deadline accuracy:** Measures whether extracted deadlines correctly match the transcript.
- **Hallucination rate:** Measures how often the system produces information not supported by the transcript.
