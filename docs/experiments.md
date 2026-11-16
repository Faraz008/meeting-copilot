## Groq run-to-run variance

### Protocol

- Provider: Groq
- Repeated full-pipeline runs: 3
- Cache: disabled (`--cache off`)
- Runs: `groq__var1`, `groq__var2`, `groq__var3`
- Dataset: six development meetings
- Configuration and matcher settings held constant.

### Results

| Metric | Mean | SD (pp) | Range |
|---|---:|---:|---:|
| Action F1 | 39.1% | 0.7 | 39–40% |
| Action precision | 29.0% | 0.8 | 29–30% |
| Action recall | 60.0% | 0.0 | 60–60% |
| Fully-correct actions (recall) | 60.0% | 0.0 | 60–60% |
| Owner accuracy | 100.0% | 0.0 | 100–100% |
| Deadline accuracy | 100.0% | 0.0 | 100–100% |
| Deadline (ambiguity-lenient) | 100.0% | 0.0 | 100–100% |
| Status accuracy | 100.0% | 0.0 | 100–100% |
| Decision F1 | 0.0% | 0.0 | 0–0% |

### Interpretation

- Action F1 standard deviation: 0.7 percentage points.
- Action precision standard deviation: 0.8 percentage points.
- Approximate two-SD thresholds: 1.4 pp for Action F1 and 1.6 pp for Action precision.
- The other reported metrics were unchanged across these three runs.

For subsequent experiments, treat improvements smaller than approximately two standard deviations as inconclusive rather than established improvements. Compare configurations using the same dataset and evaluation settings.

### Limitations

This estimate is based on only three repeated runs and six development meetings. Zero observed SD does not establish that a metric is inherently deterministic. The variance estimate is preliminary and should be revisited if more repeated runs become practical.
