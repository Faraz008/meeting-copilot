# Matcher Audit

## Groq

Incomplete runs: **0/6**

| Meeting | EXTRA/MISSED same turns? | Same underlying action? | Classification |
|---|---|---|---|
| m001 | No | No | Extra refund-policy review is transcript-supported; likely gold omission. Postgres decision is also omitted from gold. |
| s01 | No | Yes, for the feature-name check and legal check | Gold annotation omissions; main pricing action has different evidence turns. |
| s02 | No | Yes, for checklist-related tasks | Granularity mismatch and gold omissions; main checklist action is correctly extracted. |
| s03 | No | Yes, for several proposals | Granularity mismatch; extra export investigation and planning proposals are transcript-supported. |
| s04 | Partial follow-up match | Yes | Follow-up is extracted, but its wording is less specific than the gold annotation. Gold evidence turns may be misaligned; duplicate June-capacity question is an extraction error. |
| s05 | No | Yes | Granularity mismatch; extra actions are supported by the transcript but grouped into broader gold actions. |

## OpenRouter

Incomplete runs: **1/6 (s01)**

| Meeting | EXTRA/MISSED same turns? | Same underlying action? | Classification |
|---|---|---|---|
| m001 | No | No | Extra refund-policy review and Postgres decision are transcript-supported; likely gold omissions. |
| s01 | Not comparable | Not comparable | Incomplete provider call (`no providers`); no extraction output. Excluded from quality assessment. |
| s02 | No | Yes, for checklist-related tasks | Main checklist action is correct; additional supported tasks are extracted, with some duplicate checklist actions and granularity differences. |
| s03 | No | Yes, for several proposals | Main proposals are extracted; additional export, estimation, and planning items are transcript-supported. Some action fragmentation. |
| s04 | Yes — duplicate capacity question | Yes, for the weekend-coverage follow-up | Main capacity action and follow-ups are extracted. Duplicate capacity question and incorrect answered status for the weekend-coverage question. |
| s05 | No | Yes | Main summary and timestamp tasks are correct; additional posting and formatting steps are split into separate actions, including repeated commitments. |

## Ollama

Incomplete runs: **0/6**

| Meeting | EXTRA/MISSED same turns? | Same underlying action? | Classification |
|---|---|---|---|
| m001 | No | No | Postgres decision is transcript-supported but omitted from gold. |
| s01 | No | Yes, for feature-name and legal checks | Main pricing action is correct; extra tasks are supported. Some follow-up overlap. |
| s02 | No | Yes, for checklist-related tasks | Main checklist action is correct. Additional decision and follow-up extractions need some granularity and category scrutiny. |
| s03 | No | Yes, for several proposals | Gold proposal themes are captured; extra process and cost-estimation items are transcript-supported. |
| s04 | No | Yes, for the capacity and legal follow-up tasks | Main capacity action is correct. Weekend-coverage question is missed; additional forecast and legal follow-up actions are supported. |
| s05 | No | Yes, for the incident-summary and timestamp tasks | Main gold actions are captured. Additional timezone and posting steps are supported; some follow-ups overlap with actions. |

## Findings

- **Likely matcher errors:** No confirmed matcher-only errors from the provider audits.
- **Genuine model false positives:** Duplicate June-capacity question in `s04` for Groq and OpenRouter. OpenRouter also produces duplicate or fragmented checklist/posting actions in `s02` and `s05`.
- **Genuine model false negatives:** No confirmed missed underlying action from the reviewed predictions. Ollama and OpenRouter miss the gold unanswered weekend-coverage question in `s04`; Groq extracts a partial follow-up match. This remains an extraction/representation issue rather than a demonstrated matcher-only error.
- **Other extraction errors:** OpenRouter incorrectly marks the weekend-coverage question in `s04` as answered, despite the cited response saying legal review is still pending.
- **Gold annotation inconsistencies:** Gold omits transcript-supported actions or decisions in `m001`, `s01`, and `s02`. `s03` and `s05` have differences in action granularity between predictions and gold annotations. The Groq `s04` follow-up evidence turns also appear misaligned with the transcript.
- **Incomplete evaluation:** OpenRouter `s01` failed with `no providers`; its empty prediction is not treated as a model false negative.

## Controlled Matcher Comparison

The oracle, Groq, and Ollama were evaluated with both matching modes using the same `min_title=40.0`.

| Dataset | Matcher | Action precision | Action recall | Action F1 | Unresolved question recall |
|---|---|---:|---:|---:|---:|
| Oracle | Turn-aware | 100.0% | 100.0% | 100.0% | 100.0% |
| Oracle | Title-only | 100.0% | 100.0% | 100.0% | 100.0% |
| Groq | Turn-aware | 41.7% | 100.0% | 58.8% | 100.0% |
| Groq | Title-only | 41.7% | 100.0% | 58.8% | 100.0% |
| Ollama | Turn-aware | 55.6% | 100.0% | 71.4% | 50.0% |
| Ollama | Title-only | 55.6% | 100.0% | 71.4% | 50.0% |

Both matchers passed the oracle check with zero action and question false positives or false negatives. At the controlled threshold, both modes produced identical aggregate metrics for Groq and Ollama.

The earlier apparent Groq advantage for turn-aware matching came from comparing different default thresholds: 40 for turn-aware and 60 for title-only. That comparison did not isolate the effect of turn matching.

## Matcher Decision

**Frozen: turn-aware matching.**

Configuration:

- `use_turns=True`
- `min_title=40.0`
- `tol=1`
- One-to-one greedy matching, ranked by the existing title-similarity and turn-overlap score.

The controlled comparison showed no aggregate metric difference between turn-aware and title-only matching at threshold 40. Turn-aware matching is retained because it also requires evidence-turn proximity, providing an additional constraint without reducing the observed scores.

No threshold reduction or gold-title rewrite is justified by the current evidence. Do not tune the matcher against the test split.

Future evaluation runs should use this frozen configuration consistently. Any proposed matcher change should be treated as a separate experiment rather than silently changing the evaluation baseline.
