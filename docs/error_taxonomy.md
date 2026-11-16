# Error Taxonomy

## Evaluation scope

- Run: `groq__full`
- Dataset: development split (`m001`, `s01`–`s05`)
- Total error rows reviewed: **26**
- Categories assigned manually using the labeling guide and the error CSV.

## Error counts

| category | count | share | root cause | candidate fix | type |
| -------- | ----- | ----- | ---------- | ------------- | ---- |
| `gold_omission` | 15 | 57.7% | Gold annotations omit potentially valid actions, follow-ups, or questions. | Audit against the labeling guide; add only clearly supported missing items to dev gold. | label problem |
| `spurious` | 7 | 26.9% | Model extracts unsupported decisions or questions, or treats clarification as a separate item. | Tighten prompt examples for decisions, answered questions, and ownership clarification. | prompt gap |
| `wrong_kind` | 2 | 7.7% | Valid content is extracted as the wrong entity type. | Clarify action-versus-follow-up classification with prompt examples and tests. | prompt gap |
| `missed` | 1 | 3.8% | Model misses a deferred follow-up. | Add a deferral example and test to the follow-up extraction prompt. | prompt gap |
| `duplicate_or_split` | 1 | 3.8% | Model splits or duplicates work that should be represented by an existing item. | Review deduplication and task-granularity rules; test before changing thresholds. | threshold |

## Reading the numbers

- `gold_omission` is the largest category. These rows are not necessarily model errors: the prediction may be valid while the reference annotation is incomplete.
- `spurious` is the main model-side issue. The examples suggest the prompt needs clearer boundaries between decisions, questions, and ownership clarification.
- `wrong_kind` and `missed` are smaller but actionable prompt gaps, especially around follow-ups and deferred work.
- The single `duplicate_or_split` case is not enough evidence to change a threshold. Inspect more examples before tuning.
- Prioritize the gold audit and spurious-extraction prompt improvements before threshold tuning.

## Gold-label review

A `gold_omission` classification indicates that the gold file may be incomplete; it does not automatically authorize a gold edit.

- Fix a gold label only when the labeling guide clearly supports the correction.
- Record every confirmed change in `docs/gold_fixes.md` with meeting, item, old → new, and the applicable guide rule.
- If the guide does not settle the case, amend the guide first and apply the rule consistently to dev and test gold files without consulting test predictions.
- Do not change gold labels to improve model scores.
- No automatic gold changes are made by this taxonomy.

## Priority

1. **Gold audit:** review the 15 `gold_omission` rows against the guide and correct only confirmed omissions.
2. **Prompt v2:** address the 7 `spurious` rows and the smaller wrong-kind and missed-follow-up cases.
3. **Threshold review:** investigate the duplicate/split case, but do not tune from one example alone.
4. **Regression tests:** add representative cases for every confirmed prompt or code fix.
