# Per-meeting diffs

## m001

- **EXTRA** action turns [1] [proposed]: Review refund policy  _evidence: We should also review the refund policy._
- **EXTRA** decision turns [2] [None]: Use Postgres for the database  _evidence: Let's use Postgres for the database._

## s01

- **EXTRA** action turns [31] [proposed]: Raise legal cancellation wording check  _evidence: That check can be raised with legal after the copy is handed over._
- **EXTRA** action turns [34] [committed]: Review feature names  _evidence: I'll review the feature names after Sam shares the copy._
- **EXTRA** decision turns [25] [None]: Sam is the single owner of the copy  _evidence: The handoff is the important change: Sam is the single owner of the copy._

## s02

- **EXTRA** action turns [20] [committed]: Include link to release notes  _evidence: I'll include the link when I send the consolidated version._
- **EXTRA** action turns [23] [committed]: Mark security section as pending  _evidence: I'll mark the security section as pending until they respond._
- **EXTRA** action turns [30] [committed]: Link review status in the document  _evidence: I'll link the review status in the document._
- **EXTRA** decision turns [14] [None]: Monday is the only deadline for the checklist  _evidence: Correct. Please treat Monday as the only deadline._
- **EXTRA** decision turns [18] [None]: Release notes stay in their own document  _evidence: The release notes can stay in their own document._
- **EXTRA** decision turns [19] [None]: Checklist should link to release notes rather than copy them  _evidence: The checklist should link to those notes rather than copy them._
- **EXTRA** question turns [8, 9] [None]: Friday is March fourteenth, right?  _evidence: Friday is March fourteenth, right? | Yes, that's the date I had in mind._
- **EXTRA** question turns [11, 12] [None]: Would Monday be safer for the consolidated checklist too?  _evidence: Would Monday be safer for the consolidated checklist too? | Yes, change my deadline from Friday to Monday; I'll send the consolidated checkl_
- **EXTRA** question turns [21, 22] [None]: Does the security section need a separate sign-off?  _evidence: Does the security section need a separate sign-off? | Yes, security owns that sign-off, not this checklist task._

## s03

- **MISSED** action `a1` turns [7, 12, 13] tags ['proposed', 'no_owner', 'no_deadline']: Add a region filter to the analytics dashboard
- **MISSED** action `a3` turns [9, 16, 17] tags ['proposed', 'no_owner', 'no_deadline']: Investigate CSV and XLSX export support
- **MISSED** action `a4` turns [10, 11, 17] tags ['proposed', 'no_owner', 'no_deadline']: Sketch mobile dashboard layout options
- **EXTRA** follow_up turns [16] [None]: Ask data engineering about export limitation  _evidence: We could ask data engineering about the export limitation._
- **EXTRA** question turns [18] [None]: Should we rank these before the next planning session?  _evidence: Should we rank these before the next planning session?_
- **WRONG owner/status** `a2` Explore a previous-period comparison in the dashboard: gold={'owner': None, 'deadline': 'None', 'status': 'proposed'} pred={'owner': 'Nina', 'owner_raw': 'I', 'deadline': 'None', 'deadline_raw': None, 'status': 'committed', 'options': [], 'flags': ['no_deadline']}

## s04

- **MISSED** question `q1` turns [7, 13] tags []: What is the confirmed support capacity for June?
- **MISSED** question `q2` turns [16, 17, 20, 22, 25, 27] tags ['unanswered']: Is weekend support coverage included in the vendor agreement?
- **EXTRA** action turns [36] [committed]: Send vendor request follow-up  _evidence: I'll send the vendor request follow-up._
- **EXTRA** follow_up turns [15, 21] [None]: Pending: Has legal confirmed the weekend coverage clause?  _evidence: Has legal confirmed the weekend coverage clause? | Please keep that question open until legal gives us the clause._

## s05

- **EXTRA** action turns [24] [committed]: Post verified timestamp in incident channel  _evidence: I'll post the timestamp in the incident channel._
- **EXTRA** action turns [25] [committed]: Post completed summary after timestamp verification  _evidence: I'll post the completed summary after that._
- **EXTRA** action turns [31] [committed]: Include timezone note in summary  _evidence: I'll include the timezone note in the summary._
- **EXTRA** decision turns [34] [None]: Noah owns the summary and Pavel owns the timestamp check  _evidence: Noah owns the summary and Pavel owns the timestamp check._
