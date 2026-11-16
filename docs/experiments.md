# Experiments

## EXP-02: Groq run-to-run variance baseline

**Date:** 2026-11-16
**Git SHA:** Baseline commit SHA not recorded.

### Observed

Groq showed some run-to-run variation in action metrics across three repeated full-pipeline runs on six development meetings. The observed standard deviation was 0.7 percentage points for Action F1 and 0.8 percentage points for Action precision. Other reported metrics were unchanged across these three runs.

### Hypothesis

Subsequent experiment improvements should be larger than approximately two standard deviations to be treated as meaningful rather than ordinary run-to-run noise.

### Change

No model, prompt, code, matcher, or configuration changes were made. This experiment establishes a baseline for run-to-run variance.

### Protocol

- **Provider:** Groq
- **Repeated full-pipeline runs:** 3
- **Cache:** Disabled (`--cache off`)
- **Runs:** `groq__var1`, `groq__var2`, `groq__var3`
- **Dataset:** Six development meetings
- **Configuration and matcher settings:** Held constant

### Result (dev)

| Metric | Mean | SD (pp) | Range |
|---|---:|---:|---|
| Action F1 | 39.1% | 0.7 | 39–40% |
| Action precision | 29.0% | 0.8 | 29–30% |
| Action recall | 60.0% | 0.0 | 60–60% |
| Fully-correct actions (recall) | 60.0% | 0.0 | 60–60% |
| Owner accuracy | 100.0% | 0.0 | 100–100% |
| Deadline accuracy | 100.0% | 0.0 | 100–100% |
| Deadline (ambiguity-lenient) | 100.0% | 0.0 | 100–100% |
| Status accuracy | 100.0% | 0.0 | 100–100% |
| Decision F1 | 0.0% | 0.0 | 0–0% |

### Decision

Baseline established. For subsequent experiments, treat improvements smaller than approximately two standard deviations as inconclusive:

- **Action F1:** 1.4 percentage points
- **Action precision:** 1.6 percentage points

Compare configurations using the same dataset and evaluation settings.

### Note

This estimate is based on only three repeated runs and six development meetings. Zero observed standard deviation does not establish that a metric is inherently deterministic. The variance estimate is preliminary and should be revisited if more repeated runs become practical.

---

## EXP-03: Reduce spurious decisions and improve extraction boundaries

**Date:** 2026-11-16
**Git SHA:** `86b0379` (experiment starting commit)
**Branch:** `feat/baseline-ablations`

### Observed

The `spurious` category accounts for 7 of 26 reviewed error rows. Examples include ownership clarifications extracted as decisions and questions extracted despite receiving an answer within the evaluation window.

The baseline also produced ownership-clarification false-positive decisions in s01 and s05.

### Hypothesis

The extraction prompt does not sufficiently distinguish actual group decisions from ownership clarifications, responsibility statements, and factual updates.

The extraction and resolution stages also need a clear boundary: substantive questions should be extracted even if a later turn answers them, while the downstream resolution stage determines whether they remain unresolved.

Adding explicit rules and contrasting examples should reduce spurious decision predictions without losing valid questions or other correctly extracted items.

### Change

Created a new prompt version, `extract_v2.md`, with clearer rules and examples for:

- Distinguishing agreed decisions from ownership clarifications and responsibility statements.
- Requiring evidence of an actual choice or settled direction before extracting a decision.
- Preserving substantive questions for downstream resolution rather than deciding whether they were answered during extraction.
- Avoiding decisions inferred from factual statements or confirmations alone.

No code, thresholds, matcher settings, or gold labels were changed for this experiment.

### Protocol

- **Provider:** Groq
- **Baseline run:** `groq__full`
- **Candidate run:** `groq__v2`
- **Dataset:** Six development meetings (`m001`, `s01`–`s05`)
- **Split:** `dev`
- **Matcher:** `title`
- **Reference:** `groq__full`
- **Comparison:** Paired bootstrap over meetings
- **Model:** `openai/gpt-oss-120b`
- **Candidate prompt SHA:** `7ecc2b2c`
- **Git SHA recorded by candidate run:** `86b0379` (dirty working tree)

Both runs were compared using the same title matcher and development split.

### Result (dev)

| Metric | Baseline (`groq__full`) | Candidate (`groq__v2`) |
|---|---:|---:|
| Action F1 | 59% [48–68] | 52% [44–60] |
| Action precision | 42% [32–52] | 41% [32–58] |
| Action recall | 100% [100–100] | 70% [40–100] |
| Fully-correct actions (recall) | 100% [100–100] | 60% [20–100] |
| Owner accuracy | 100% [100–100] | 86% [50–100] |
| Deadline accuracy | 100% [100–100] | 100% [100–100] |
| Deadline (ambiguity-lenient) | — | 100% [100–100] |
| Status accuracy | — | 86% [50–100] |
| Decision F1 | 0% [0–0] | 0% [0–0] |
| Question F1 | — | 25% [0–80] |
| Unresolved-question recall | 100% [100–100] | 50% [0–100] |
| Unresolved-question precision | — | 50% [0–100] |
| Ungrounded items in output | 0% [0–0] | 0% [0–0] |
| Raw hallucination rate (pre-filter) | — | 0% [0–0] |
| Schema/JSON failure rate | — | 0% [0–0] |
| Repairs / meeting | — | 0.0 [0.0–0.0] |
| Incomplete runs | — | 0% [0–0] |

The candidate processed six meetings, with 10 gold actions and 17 predicted actions.

**Paired bootstrap differences vs baseline:**

| Metric | Difference | 95% paired bootstrap interval |
|---|---:|---:|
| Action F1 | -7.0 pp | [-20.5, +5.6] |
| Action precision | -0.5 pp | [-3.9, +8.3] |
| Action recall | -30.0 pp | [-60.0, +0.0] |
| Fully-correct action recall | -40.0 pp | [-80.0, +0.0] |
| Owner accuracy | -14.3 pp | [-50.0, +0.0] |
| Deadline accuracy | +0.0 pp | [+0.0, +0.0] |
| Decision F1 | +0.0 pp | [+0.0, +0.0] |
| Unresolved-question recall | -50.0 pp | [-100.0, +0.0] |
| Ungrounded items in output | +0.0 pp | [+0.0, +0.0] |

All paired bootstrap intervals include zero or have zero as an endpoint. The observed differences therefore do not establish statistically clear deterioration, although the practical metric pattern is unfavorable.

### Hard-case results

| Tag | Cases | Found | Fully correct |
|---|---:|---:|---:|
| deferred | 1 | 1/1 | 1/1 |
| no_deadline | 7 | 4/7 | 3/7 |
| no_owner | 4 | 1/4 | 0/4 |
| proposed | 4 | 1/4 | 0/4 |
| relative_date | 1 | 1/1 | 1/1 |
| retraction | 1 | 1/1 | 1/1 |
| revision | 2 | 2/2 | 2/2 |
| unanswered | 1 | 0/1 | 0/1 |

The candidate handled the deferred, relative-date, retraction, and revision cases correctly. However, it struggled with no-owner and proposed actions, and missed the unanswered-question case.

### Per-meeting observations

| Meeting | Actions TP/FP/FN | Decisions TP/FP/FN | Questions TP/FP/FN | Mismatches |
|---|---:|---:|---:|---:|
| m001 | 1/1/0 | 0/1/0 | 1/0/0 | 0 |
| s01 | 1/2/0 | 0/1/0 | 0/0/0 | 0 |
| s02 | 1/3/0 | 0/3/0 | 0/3/0 | 0 |
| s03 | 1/0/3 | 0/0/0 | 0/1/0 | 1 |
| s04 | 1/1/0 | 0/0/0 | 0/0/2 | 0 |
| s05 | 2/3/0 | 0/1/0 | 0/0/0 | 0 |

Decision F1 remained at zero. The candidate did not solve the false-positive decision problem: decision predictions remained false positives across several meetings. It also missed three gold actions in s03 and two gold questions in s04.

### Decision

Reject `extract_v2` and retain `extract_v1` as the baseline.

The candidate's Action F1 decreased from 59% to 52%, action recall from 100% to 70%, fully-correct action recall from 100% to 60%, owner accuracy from 100% to 86%, and unresolved-question recall from 100% to 50%.

Decision F1 remained at 0%, so the intended reduction in spurious decisions was not achieved. The candidate also missed several actions and questions that the baseline had captured.

The paired confidence intervals include zero or have zero as an endpoint, so this is a practical engineering decision based on the observed regression pattern, not a claim of statistically significant deterioration.

### Note

This experiment covers six development meetings and one run per prompt version. The small sample and run-to-run variability limit confidence in metric differences.

The EXP-02 noise-floor estimates are approximately 1.4 percentage points for Action F1 and 1.6 percentage points for Action precision. These estimates are preliminary and should not be treated as formal significance thresholds.

No test-set results were used. The experiment does not establish whether the candidate generalizes to unseen meetings.
