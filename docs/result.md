# Results

## Evaluation scope

- Split: development
- Meetings: 6 (`m001`, `s01`–`s05`)
- Gold actions: 10
- Providers: Groq, OpenRouter, Ollama (Qwen3 4B Q4_K_M)
- Held-out test results are reserved for Week 5.
- Metrics are micro-averaged over meetings; reported confidence intervals are 95% bootstrap intervals over meetings.

## Baseline vs. pipeline

The baseline and full pipeline are compared using the title-only matcher in this experiment. The turn-aware full-pipeline results are also shown separately for reference.

| Model | System | Matcher | Action F1 | Precision | Recall | Fully-correct actions | Owner accuracy | Deadline accuracy | Ungrounded |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Groq | Baseline | Title | 44% [24–69] | 35% [22–64] | 60% [20–100] | 60% [20–100] | 100% | 100% | — |
| Groq | Full | Title | 53% [47–57] | 38% [32–43] | 90% [80–100] | 90% [80–100] | 100% | 100% | 0% |
| Groq | Full | Turns | 59% [48–68] | 42% [32–52] | 100% | 100% | 100% | 100% | 0% |
| OpenRouter | Baseline | Title | 33% [12–56] | 25% [11–40] | 50% [13–100] | 50% [13–100] | 100% | 100% | — |
| OpenRouter | Full | Title | 35% [24–44] | 22% [15–32] | 80% [56–100] | 80% [56–100] | 100% | 100% | 0% |
| OpenRouter | Full | Turns | 39% [24–53] | 25% [15–38] | 90% [57–100] | 90% [57–100] | 100% | 100% | 0% |
| Ollama | Baseline | Title | 86% [57–100] | 82% [50–100] | 90% [67–100] | 20% [0–56] | 56% [20–100] | 67% [17–93] | — |
| Ollama | Full | Title | 71% [58–86] | 56% [41–75] | 100% | 100% | 100% | 100% | 0% |
| Ollama | Full | Turns | 71% [58–86] | 56% [41–75] | 100% | 100% | 100% | 100% | 0% |

The OpenRouter `s01` full-pipeline run was incomplete because the provider returned `no providers`. Its quantitative results should therefore be interpreted with that limitation in mind.

## What each component buys

The following tables use the turn-aware matcher. The full pipeline is the reference configuration.

### Groq

| Configuration | Action F1 | Precision | Recall | Fully-correct recall | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full pipeline | 59% | 42% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| No grounding | 59% | 42% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| No code dates | 59% | 42% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| No pass 2 | 59% | 42% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| Naive pipeline | 59% | 42% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |

All four ablations produced exactly the same reported aggregate metrics and paired differences as the full pipeline.

### OpenRouter

| Configuration | Action F1 | Precision | Recall | Fully-correct recall | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full pipeline | 39% | 25% | 90% | 90% | 100% | 100% | 0% | 50% | 0% |
| No grounding | 39% | 25% | 90% | 90% | 100% | 100% | 0% | 50% | 0% |
| No code dates | 39% | 25% | 90% | 90% | 100% | 100% | 0% | 50% | 0% |
| No pass 2 | 39% | 25% | 90% | 90% | 100% | 100% | 0% | 100% | 0% |
| Naive pipeline | 39% | 25% | 90% | 90% | 100% | 100% | 0% | 100% | 0% |

Removing pass two and using the naive pipeline both increased observed unresolved-question recall from 50% to 100%. The paired intervals for these changes include zero.

### Ollama (Qwen3 4B Q4_K_M)

| Configuration | Action F1 | Precision | Recall | Fully-correct recall | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full pipeline | 71% | 56% | 100% | 100% | 100% | 100% | 0% | 50% | 0% |
| No grounding | 71% | 56% | 100% | 100% | 100% | 100% | 0% | 50% | 3% |
| No code dates | 71% | 56% | 100% | 100% | 100% | 100% | 0% | 50% | 0% |
| No pass 2 | 71% | 56% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| Naive pipeline | 71% | 56% | 100% | 100% | 100% | 100% | 0% | 100% | 3% |

Removing grounding increased the observed ungrounded rate from 0% to 3%. Removing pass two increased unresolved-question recall from 50% to 100%. The naive pipeline showed both changes.

### Paired differences vs. full pipeline

The following table preserves the non-zero paired differences and their 95% bootstrap intervals. All unlisted metric differences for each configuration were exactly `+0.0 [0.0, 0.0]` in the source reports.

| Model | Ablation | Metric | Δ (percentage points) | 95% paired CI |
|---|---|---|---:|---:|
| Groq | No grounding | All reported metrics | 0.0 | [0.0, 0.0] |
| Groq | No code dates | All reported metrics | 0.0 | [0.0, 0.0] |
| Groq | No pass 2 | All reported metrics | 0.0 | [0.0, 0.0] |
| Groq | Naive pipeline | All reported metrics | 0.0 | [0.0, 0.0] |
| OpenRouter | No grounding | All reported metrics | 0.0 | [0.0, 0.0] |
| OpenRouter | No code dates | All reported metrics | 0.0 | [0.0, 0.0] |
| OpenRouter | No pass 2 | Unresolved-question recall | +50.0 | [0.0, +100.0] |
| OpenRouter | Naive pipeline | Unresolved-question recall | +50.0 | [0.0, +100.0] |
| Ollama | No grounding | Ungrounded items in output | +2.8 | [0.0, +7.3] |
| Ollama | No code dates | All reported metrics | 0.0 | [0.0, 0.0] |
| Ollama | No pass 2 | Unresolved-question recall | +50.0 | [0.0, +100.0] |
| Ollama | Naive pipeline | Unresolved-question recall | +50.0 | [0.0, +100.0] |
| Ollama | Naive pipeline | Ungrounded items in output | +2.8 | [0.0, +7.3] |

Where the paired confidence interval includes zero, report **no detectable effect on this dataset**. The grounding-related increase for Ollama is an observed difference, but its interval also touches zero, so it is not conclusive under this rule.

The source reports contain no numeric spurious-actions-per-negative-meeting result (`—`), so this metric is not interpreted as zero.

## Noise floor

Three repeated Groq full-pipeline runs were performed with cache disabled:

- Runs: `groq__var1`, `groq__var2`, `groq__var3`
- Action F1: **39.1% ± 0.7 pp**
- Action precision: **29.0% ± 0.8 pp**
- Action recall: **60.0% ± 0.0 pp**
- Fully-correct action recall: **60.0% ± 0.0 pp**
- Owner accuracy: **100.0% ± 0.0 pp**
- Deadline accuracy: **100.0% ± 0.0 pp**
- Status accuracy: **100.0% ± 0.0 pp**
- Decision F1: **0.0% ± 0.0 pp**

Approximate two-standard-deviation thresholds are 1.4 percentage points for Action F1 and 1.6 percentage points for precision. This estimate is preliminary because it is based on three runs and six meetings.

**Consistency warning:** The repeated Groq runs report Action F1 of 39.1% and recall of 60%, whereas the saved Groq turn-aware full report reports 59% Action F1 and 100% recall. These are not directly comparable until the run configuration, gold files, matcher settings, and scoring version are verified. Do not use the 39.1% mean as the noise floor for interpreting the 59% result yet.

## Reading these numbers

no_code_dates produces no measurable change in deadline accuracy on this dataset, but deadline accuracy is already 100% across the runs, so this does not establish that code-based date handling is unnecessary. The dl_invented and dl_wrong counts should be checked alongside accuracy to see whether any deadline errors are being introduced or corrected. Removing grounding raises the ungrounded rate for Ollama, but the observed increase is small and its interval includes zero; there is no detectable effect on precision in these runs. Removing pass 2 does not produce a detectable change in action precision or duplicate-related metrics, but unresolved-question recall is higher for OpenRouter and Ollama; the intervals include zero, so this is not conclusive evidence that pass 2 harms question detection. Overall, most component ablations show no detectable effect on this dataset, and the small sample means these results should be treated as descriptive rather than proof that a component is unnecessary

## Limitations

- The development set contains only six meetings and ten gold actions.
- Confidence intervals over six meetings are wide and provide limited precision.
- OpenRouter's `s01` run was incomplete because no provider was available.
- The Groq variance experiment and saved Groq full report have inconsistent metrics; resolve this before using the variance estimate as a comparison threshold.
- Zero observed differences in an ablation do not prove that a component is unnecessary; effects may be too small or too rare to appear in this dataset.
- These are development-set findings, not held-out test results.
