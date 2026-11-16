# Evaluation protocol

## Gold labels and final meeting state

Gold labels describe the **final state** of a meeting. Superseded action items and reversed decisions are excluded from predictions before scoring. Only the final state is compared.

Retraction handling is reflected in owner and deadline accuracy on tagged items.

## Matching

Two matching strategies are used:

- **Turn + title matcher:** Requires evidence turns to be within ±1 of the gold turns and titles to be sufficiently similar. This is the stricter and more reliable matcher.
- **Title-only matcher:** Matches using title similarity alone. It is used because the baseline does not provide evidence turns.

The headline baseline-versus-pipeline comparison uses the title-only matcher for both systems to keep the comparison fair. Ablations between pipeline variants use the turn + title matcher.

Matching uses a greedy one-to-one assignment in descending score order. Every matched pair is saved for manual inspection and auditing.

## Metrics and confidence intervals

Metrics are micro-averaged across meetings. Confidence intervals are calculated using bootstrap resampling over meetings.

With approximately 17 development meetings, a 3-point F1 difference should not be treated as strong evidence of improvement. Confidence intervals provide additional context for interpreting these differences.
