# Dataset splits

The dataset is split at the meeting level. Each meeting belongs to exactly one split.

## Development

Used for prompt iteration, parser development, debugging, and threshold selection.

Synthetic meetings:
- s01
- s02
- s03
- s04
- s05

## Test

Frozen evaluation set. Used only for final evaluation after the development workflow is finalized.

Synthetic meetings:
- s06
- s07
- s08
- s09
- s10
- s11
- s12
- s13
- s14
- s15

Test meetings must not be used for prompt tuning, model selection, threshold selection, or iterative debugging.

## Split policy

- Meetings are assigned to exactly one split.
- A meeting must never appear in both dev and test.
- Hard-case categories are represented across both splits.
- Real meetings retain their original meeting IDs.
- Source attribution and license metadata are recorded for every real meeting.
- m001 is retained as the original pilot meeting in development.

## Freeze rule

Never tune on the test split.

Any change to test labels or split membership must be documented and justified.
