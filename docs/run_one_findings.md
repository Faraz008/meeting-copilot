# Live Evaluation Findings

## Evaluation setup

- Dataset: Development transcripts (`s01`, `s02`, `s03`)
- Provider: Groq
- Prompt: `extract_v1`
- Grounding: Enabled
- Pass 2: Enabled
- Deadline resolver: Rules
- Evaluation: Manual comparison against available gold annotations

## s01 — Pricing copy handoff

### Correct predictions
- Sam correctly identified as the owner of the revised pricing copy.
- Friday deadline correctly resolved to `2025-03-14`.
- Priya-to-Sam ownership handoff represented correctly.
- Dan's feature-name review extracted with grounded evidence.
- Legal cancellation check correctly classified as proposed.
- Legal question retained as unanswered.

### Findings
- Core action, ownership and deadline extraction worked correctly.
- Additional predictions include a feature-name action, legal proposal, decision and open question.
- These predictions have transcript evidence but are not represented in the current gold annotations.
- Gold coverage should be checked before treating these as false positives.

## s02 — Checklist deadline revision

### Correct predictions
- Dan correctly identified as the checklist owner.
- Revised Monday deadline correctly resolved to `2025-03-17`.
- Original Friday commitment retained as superseded.
- Original action correctly linked to its replacement.
- Security question answered using grounded evidence.

### Findings
- Weekend-comments commitment extracted separately.
- Release-notes link and review-status link extracted as separate actions.
- Security sign-off decision and follow-up were also extracted.
- These additional predictions are grounded but absent from the current gold annotations.

### Potential decision-judging issue
- The decision stating that Monday replaces Friday was marked `superseded`.
- Its evidence says the earlier Friday date is superseded.
- This suggests a possible status interpretation error in decision judging.
- Review the decision-judging prompt and status mapping.

## s03 — Dashboard planning

### Correct predictions
- Region filter proposal extracted.
- CSV/XLSX export investigation extracted.
- Mobile layout proposal extracted.

### Potential extraction and reconciliation issues
- The gold previous-period comparison action was not clearly matched.
- Export investigation appears split into:
  - Investigate CSV/XLSX export support.
  - Ask data engineering about the export limitation.
- Mobile layout work appears split into:
  - Create compact mobile summary.
  - Sketch two layout options.
- The estimate comparison cost action may be a separate supporting task or part of the previous-period comparison proposal.
- Carrying proposals into planning was extracted as a committed action.
- Ranking proposals was extracted as an open question.
- Revisiting prioritization was extracted as a follow-up.

### Findings
- Proposal detection is working.
- Related multi-turn statements may be extracted as separate actions instead of being consolidated.
- The previous-period comparison needs closer inspection against the transcript.
- Do not lower deduplication thresholds without checking whether the separate actions represent distinct commitments.

## Cross-meeting findings

| Area | Observation | Follow-up |
|---|---|---|
| Ownership | Main gold owners correctly resolved in s01 and s02 | No change |
| Deadlines | Friday and revised Monday dates correctly resolved | No change |
| Grounding | No candidates rejected in live runs | Continue monitoring |
| Supersession | Friday commitment correctly linked to Monday replacement in s02 | No change |
| Decision judging | Possible incorrect superseded status in s02 | Inspect judge prompt and status semantics |
| Deduplication | Possible over-segmentation of related proposals in s03 | Inspect reconciliation logic |
| Extraction | Previous-period comparison not clearly matched in s03 | Inspect prompt and transcript |
| Question judging | Security question correctly answered in s02 | No change |
| Gold coverage | Additional grounded predictions absent from s01 and s02 gold | Verify annotation completeness |

## Confirmed implementation bugs

- None confirmed from these three runs.

## Prompt improvement candidates

- Clarify how decision status should be assigned when an earlier decision is replaced by a newer one.
- Improve extraction of multi-turn proposals and their supporting statements.
- Clarify when a supporting step belongs to an existing action rather than a separate commitment.
- Improve recognition of previous-period comparison proposals.

## Threshold and heuristic candidates

- Review semantic merging of related multi-turn proposals.
- Check whether current deduplication rules distinguish supporting steps from independent commitments.
- Do not change fuzzy thresholds based on these three examples alone.

## Deferred work

- Systematic precision, recall and F1 evaluation.
- Prompt ablation experiments.
- Threshold tuning against a larger evaluation set.
- Broader dataset evaluation.
- Gold annotation completeness review.

## conclusion

- Main ownership and deadline cases worked correctly.
- Grounding behaved correctly in the observed runs.
- Decision judging may incorrectly interpret supersession.
- s03 suggests possible over-segmentation of related proposals.
- Gold annotation coverage needs verification before treating unmatched predictions as false positives.
- No implementation changes are justified until the suspected issues are reproduced.
