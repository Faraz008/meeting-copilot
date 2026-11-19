# Evaluation Results

## Evaluation scope

- Development set: six meetings (`m001`, `s01`–`s05`)
- Providers: Groq, OpenRouter, and Ollama
- Prompts: `extract_v1` and `extract_v2`
- Evaluation: title matcher and turn matcher
- Test split: not used for tuning or prompt selection

## v1 results

### Provider comparison

| Provider | Configuration | Action F1 | Notes |
|---|---|---:|---|
| Groq | Baseline, title matcher | 44% | |
| Groq | Full pipeline, title matcher | 53% [47–57] | |
| Groq | Full pipeline, turn matcher | 59% [48–68] | Recall 100% |
| OpenRouter | Baseline, title matcher | 33% | |
| OpenRouter | Full pipeline, title matcher | 35% | |
| OpenRouter | Full pipeline, turn matcher | 39% | |
| Ollama | Baseline, title matcher | 86% | |
| Ollama | Full pipeline, title matcher | 71% | |

### Component ablations

The v1 ablation results showed limited measurable differences between the full pipeline and several reduced configurations.

- Groq: removing grounding, code dates, or pass 2 did not materially change the reported aggregate metrics.
- OpenRouter and Ollama: removing pass 2 increased unresolved-question recall from 50% to 100% in the observed runs.
- Some reduced configurations also showed changes in ungrounded output. These results should be interpreted alongside the small evaluation set.

### Run-to-run variance

The repeated Groq runs produced the following measurements:

| Metric | Mean | Standard deviation |
|---|---:|---:|
| Action F1 | 39.1% | 0.7 pp |
| Action precision | 29.0% | 0.8 pp |
| Action recall | 60.0% | 0.0 pp |
| Fully-correct action recall | 60.0% | 0.0 pp |

These estimates use only three runs over six development meetings. Zero observed standard deviation does not establish that the system is deterministic.

The repeated-run results also differ from the older saved Groq full-pipeline report, which recorded 59% action F1 and 100% recall. The runs may differ in prompt, configuration, matcher, or evaluation state. Therefore, the variance estimates should not be treated as a universal noise floor for every Groq result.

---

## v2 results

The following results are from the `extract_v2` prompt ablation runs.

### Provider comparison — title matcher

| Provider | Configuration | Action F1 | Precision | Recall | Fully-correct recall | Owner accuracy | Deadline accuracy | Unresolved-Q recall |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Groq | Baseline | 44% | 35% | 60% | 60% | 100% | 100% | 50% |
| Groq | Full pipeline | 52% | 41% | 70% | 60% | 86% | 100% | 50% |
| OpenRouter | Baseline | 60% | 45% | 90% | 60% | 67% | 100% | 100% |
| OpenRouter | Full pipeline | 47% | 35% | 70% | 50% | 71% | 100% | 50% |
| Ollama | Baseline | 95% | 91% | 100% | 30% | 60% | 70% | 100% |
| Ollama | Full pipeline | 69% | 53% | 100% | 100% | 100% | 100% | 50% |

**Important OpenRouter limitation:** `s01` was incomplete in the full-pipeline run and in the no-grounding and no-code-dates runs. Those configurations therefore do not have complete, equivalent meeting coverage to the baseline. Their aggregate comparisons should be treated as provisional.

### Provider comparison — turn matcher

| Provider | Configuration | Action F1 | Precision | Recall | Fully-correct recall | Owner accuracy | Deadline accuracy | Unresolved-Q recall |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Groq | Full pipeline | 44% | 35% | 60% | 60% | 100% | 100% | 50% |
| OpenRouter | Full pipeline | 33% | 25% | 50% | 50% | 100% | 100% | 50% |
| OpenRouter | No pass 2 | 32% | 21% | 60% | 60% | 100% | 100% | 100% |
| Ollama | Full pipeline | 69% | 53% | 100% | 100% | 100% | 100% | 50% |

The turn-matcher results for Groq and Ollama were unchanged across the reported component ablations on the main action metrics. OpenRouter's no-pass-2 configuration showed a small change in action metrics and higher unresolved-question recall, but the paired confidence intervals include zero.

### Component ablations — v2

| Provider | Ablation | Observed result |
|---|---|---|
| Groq | No grounding | Same main metrics as full pipeline |
| Groq | No code dates | Same main metrics as full pipeline |
| Groq | No pass 2 | Same action metrics; unresolved-question recall increased from 50% to 100% |
| Groq | Naive pipeline | Same action metrics as no-pass-2; unresolved-question recall increased to 100% |
| OpenRouter | No grounding | Same reported metrics as full pipeline; `s01` incomplete |
| OpenRouter | No code dates | Same reported metrics as full pipeline; `s01` incomplete |
| OpenRouter | No pass 2 | Action metrics changed slightly; unresolved-question recall increased from 50% to 100% |
| OpenRouter | Naive pipeline | Same reported action metrics as no-pass-2 |
| Ollama | No grounding | Turn-matcher ungrounded rate increased from 0% to 3% |
| Ollama | No code dates | Same main metrics as full pipeline |
| Ollama | No pass 2 | Same action metrics; unresolved-question recall increased from 50% to 100% |
| Ollama | Naive pipeline | Similar to no-pass-2; turn-matcher ungrounded rate was 3% |

The no-grounding and no-code-dates configurations generally produced the same aggregate action metrics as the full pipeline in these runs. The small observed changes in ungrounded output and unresolved-question recall should not be treated as conclusive where the paired confidence intervals include zero.

### Paired comparisons and confidence intervals

| Provider | Comparison | Metric | Difference | 95% interval |
|---|---|---|---:|---:|
| Groq | Full vs baseline | Action F1 | +7.4 pp | [-9.7, +21.5] |
| Groq | Full vs baseline | Action precision | +5.9 pp | [-18.1, +23.1] |
| Groq | Full vs baseline | Action recall | +10 pp | [0, +20] |
| Groq | Full vs baseline | Fully-correct recall | 0 pp | [0, 0] |
| Groq | Full vs baseline | Owner accuracy | -14.3 pp | [-50, 0] |
| Groq | No pass 2 vs full | Unresolved-Q recall | +50 pp | [0, +100] |
| OpenRouter | Full vs baseline | Action F1 | -13.3 pp | [-19, -7.1] |
| OpenRouter | Full vs baseline | Action precision | -10 pp | [-16.7, +1.6] |
| OpenRouter | Full vs baseline | Action recall | -20 pp | [-44.4, 0] |
| OpenRouter | Full vs baseline | Fully-correct recall | -10 pp | [-42.9, 0] |
| OpenRouter | Full vs baseline | Unresolved-Q recall | -50 pp | [-100, 0] |
| OpenRouter | No pass 2 vs full, turn matcher | Action F1 | -1.8 pp | [-8.3, +3.6] |
| OpenRouter | No pass 2 vs full, turn matcher | Action recall | +10 pp | [0, +42.9] |
| OpenRouter | No pass 2 vs full, turn matcher | Unresolved-Q recall | +50 pp | [0, +100] |
| Ollama | Full vs baseline | Action F1 | -26.3 pp | [-42.9, -11.9] |
| Ollama | Full vs baseline | Action precision | -38.3 pp | [-60, -19.5] |
| Ollama | Full vs baseline | Fully-correct recall | +70 pp | [+22.2, +100] |
| Ollama | Full vs baseline | Owner accuracy | +40 pp | [0, +80] |
| Ollama | Full vs baseline | Deadline accuracy | +30 pp | [+5.9, +83.3] |

OpenRouter's full-pipeline comparisons against its baseline are affected by the incomplete `s01` run. They should not be interpreted as clean paired comparisons across the same six meetings.

### Reading these numbers

`no_code_dates` produces no measurable change in the reported deadline accuracy on this dataset. This does not establish that code-based date resolution is unnecessary; the evaluation set may not contain enough cases where it changes the outcome. Removing grounding has little effect on the main aggregate metrics in most runs, although Ollama shows a small increase in ungrounded output in the reduced configuration. Removing pass 2 increases unresolved-question recall from 50% to 100% in some provider runs, but the paired confidence intervals include zero, so this is not conclusive evidence that pass 2 is harmful. Ollama's baseline has higher action F1 and precision, but the full pipeline has substantially better fully-correct action recall, owner accuracy, and deadline accuracy. OpenRouter's incomplete `s01` runs make its full-pipeline comparisons less reliable. Overall, these results are descriptive rather than proof that a component is unnecessary.

---

## What I tried that didn't work

### 1. Threshold tuning

I swept `dedupe_title`, `supersede_hint`, `supersede_cue`, and `grounding` individually across three values each.

For both v1 and v2, the threshold sweeps produced identical reported aggregate metrics across the tested values. There was no measurable improvement in action F1, fully-correct action recall, decision F1, unresolved-question recall, or ungrounded rate.

**Outcome:** Kept the existing threshold defaults rather than selecting a value based on negligible or nonexistent changes.

### 2. The v2 prompt changes

The v2 prompt introduced stricter distinctions between decisions and ownership clarifications, and changed how answered and unresolved questions were handled.

The Groq v2 run did not improve the overall result over v1. Action F1 decreased from 59% to 52%, action recall decreased from 100% to 70%, fully-correct action recall decreased from 100% to 60%, and unresolved-question recall decreased from 100% to 50%. Decision F1 remained at 0%.

The v2 prompt also showed regressions on no-owner, proposed, and unanswered-question cases. Although some individual cases improved, the overall pattern did not satisfy the acceptance criteria.

**Outcome:** Retained v1 as the baseline and treated v2 as a negative prompt experiment rather than promoting it.

### 3. Removing completed-item filtering

The completed-item filter experiment produced identical aggregate metrics to the full configuration. The development gold data contained no `past_tense_negative` cases, so the experiment did not meaningfully test the intended behavior.

**Outcome:** No evidence of improvement. Revisit this experiment only when the development set contains appropriately labeled examples.

### 4. Removing pipeline components

Removing grounding and code-date handling generally did not change the aggregate action metrics in the observed v2 runs. Removing pass 2 changed unresolved-question recall for some providers, but the confidence intervals were too wide to establish a reliable improvement.

The Ollama baseline also demonstrated that a higher action F1 does not necessarily mean better end-to-end extraction: its full pipeline had lower F1 but much higher fully-correct action recall and owner/deadline accuracy.

**Outcome:** No component was removed based only on these small ablation results.

### 5. Cross-provider comparisons

The providers behaved differently across the same prompt and pipeline configurations. OpenRouter also had incomplete `s01` runs in several configurations, which prevents a clean comparison with its baseline.

**Outcome:** Avoid treating one provider's aggregate score as proof that it is universally better. Complete, same-meeting runs are needed before drawing stronger conclusions.

## Operational stats

The call log contained **375 logged records** for the selected final runs. Of these, **202 were live provider attempts** after excluding cached records.

| Provider | Live attempts | Successful attempts | Attempts with `attempt > 1` | Median successful latency | P95 successful latency | Errors |
|---|---:|---:|---:|---:|---:|---|
| Groq | 43 | 23 | 20 | 2.1 s | 3.8 s | 20 `RateLimited` |
| Ollama | 37 | 37 | 0 | 6.8 s | 83.1 s | None |
| OpenRouter | 122 | 39 | 63 | 44.1 s | 86.6 s | 72 `RateLimited`, 11 `EmptyResponse` |

### Repairs and call purpose

| Provider | Repair calls | Calls by purpose |
|---|---:|---|
| Groq | 0 | baseline: 11; extract: 24; judge_q: 6; judge_d: 2 |
| Ollama | 1 | baseline: 10; repair: 1; extract: 10; judge_d: 9; judge_q: 7 |
| OpenRouter | 0 | baseline: 10; extract: 104; judge_d: 5; judge_q: 3 |

### Operational interpretation

- **Groq:** 20 of 43 live attempts were rate-limited. Successful attempts had a low median latency of 2.1 seconds, but rate limits caused substantial retry activity.
- **Ollama:** All 37 live attempts succeeded, with no attempts recorded after the first attempt. Its median successful latency was 6.8 seconds, although the 83.1-second P95 indicates a long tail.
- **OpenRouter:** 39 of 122 live attempts succeeded. Rate limiting was the largest recorded failure category, with 72 `RateLimited` and 11 `EmptyResponse` outcomes. Successful calls were considerably slower than the other providers.
- **Repairs:** One repair call was recorded, on Ollama. No repair calls were recorded for Groq or OpenRouter.

These figures describe the logged calls, not the probability that an entire meeting run will complete successfully. An attempt with `attempt > 1` is counted as a later attempt in the log; it should not be interpreted as a count of unique requests that required retries. Latency statistics include successful attempts only. The call log also does not establish provider uptime or future reliability.

## Overall conclusion

The v2 prompt and threshold experiments did not provide enough evidence to replace v1 as the baseline. The ablations suggest that some pipeline components had little measurable effect on this small development set, while pass 2 may affect unresolved-question recall. These findings are useful for directing future experiments, but they are not sufficient to justify removing components or changing the production configuration.

The operational logs show different provider trade-offs: Ollama had the strongest observed call-level success record but a long latency tail; Groq was faster on successful calls but encountered rate limits; OpenRouter experienced substantial rate limiting, empty responses, and higher latency. These are observations from this particular evaluation run, not guarantees of future provider reliability.

All conclusions are limited by the small development set and, for OpenRouter, incomplete runs.
