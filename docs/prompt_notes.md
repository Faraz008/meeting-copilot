# Prompt Evaluation Notes

## Evaluation scope

- Development transcripts reviewed: `s01`–`s04`
- Providers: Groq and OpenRouter
- Comparison: manual review against gold annotations
- Test split: not used

## Observations

| Meeting | Provider | Observed failure | Fix to consider |
|---|---|---|---|
| `s01` | Groq | Owner returned as `"I"` instead of a person’s name. Extra candidates appeared for feature-name checks, legal wording, and related questions. | Keep `owner_raw` as spoken and resolve identity downstream using `owner_turn_idx`. Tighten the distinction between actual commitments and discussion or suggestions. |
| `s01` | OpenRouter | The original pricing-copy task and revised version both appeared, with the original marked superseded. | Preserve superseded status when a commitment is explicitly replaced. Avoid treating the earlier version as an active task. |
| `s02` | Groq | Correctly captured the checklist deadline revision from Friday to Monday, with the Monday task marked committed. Also extracted extra actions for the release-notes link, review-status link, and keeping comments open. | Preserve explicit deadline revisions. Avoid turning every supporting instruction or document detail into a separate action unless it is independently committed work. |
| `s02` | Groq | Extracted a security sign-off decision/question and a follow-up to retain the date change in notes, although the gold contains no decisions, questions, or follow-ups. | Do not promote discussion about dependencies or administrative notes into separate records unless they meet the extraction criteria. |
| `s02` | OpenRouter | Captured the Friday-to-Monday checklist revision and several supporting actions, including flagging cross-team dependencies and marking the security section pending. | Distinguish the main committed task from supporting details. Avoid splitting one task into multiple action items. |
| `s03` | Groq | Missed the proposed previous-period comparison action. It captured the region filter, export investigation, and mobile-layout work. | Retain proposed feature ideas even when they have no owner or deadline. |
| `s03` | OpenRouter | Captured all four gold action items, but also produced additional administrative actions, decisions, a question, and a follow-up not present in the gold. | Avoid promoting general process statements or planning discussion into separate actions and decisions unless they represent distinct commitments or decisions. |
| `s04` | Groq | Extracted the June capacity question but did not distinguish that it had subsequently been answered. | Determine question status from the full discussion, including later answers. |
| `s04` | Groq | Produced a duplicate June-capacity question and a generic follow-up that lost the specific weekend-coverage condition. | Deduplicate questions about the same issue and preserve the specific subject and condition of deferred follow-ups. |
| `s04` | OpenRouter | The visible output begins with an action to "Note which questions have a direct answer" (`owner_raw: "I"`, turn 4). This action is not present in the gold action list, which contains only Chris requesting confirmed June support capacity. | Avoid extracting general meeting-process instructions as action items unless someone explicitly commits to performing them. |

## Cross-meeting notes

- Owner phrases such as `"I"` are raw evidence, not resolved identities. Keep identity resolution downstream.
- Proposed ideas can be valid action candidates without an owner or deadline.
- When a commitment is revised, preserve the earlier version as superseded rather than leaving both versions active.
- Supporting details should not automatically become separate action items.
- Questions must be evaluated against the full discussion, not only the turn where they were first raised.
- Follow-ups should retain their specific subject and condition instead of becoming generic reminders.
- Extra administrative statements can inflate extraction results. Extract them only when they represent a distinct action, decision, question, or follow-up.

## Evaluation limitations

- Some OpenRouter outputs for `s01`, `s02`, and `s04` were truncated in the captured logs. Provider-specific conclusions for those incomplete outputs are limited to the visible content.
- The s04 OpenRouter response was truncated. Only its first visible action could be assessed; the remaining output is unknown.
- The available s02 OpenRouter output was incomplete, so its full output has not been assessed against the gold.
- These four development meetings are not enough to conclude that one provider is generally better.

## Prompt changes

No prompt changes are recorded as completed here. The observations above identify specific candidate fixes. Validate each change against the same development examples before keeping it.

**Test split remains untouched.**
