### Baseline vs pipeline: held-out test, groq

Matcher: **title**. Values are micro-averaged over 10 meetings; brackets are 95% bootstrap CIs over meetings.

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 72% [58%–83%] | 56% [40%–71%] | 100% [100%–100%] | 61% [30%–100%] | 100% [100%–100%] | 96% [86%–100%] | 23% [6%–39%] | 100% [100%–100%] | – | 0.0 [0.0–0.0] |
| full | 68% [49%–87%] | 52% [33%–78%] | 96% [82%–100%] | 83% [64%–97%] | 100% [100%–100%] | 86% [70%–100%] | 40% [0%–100%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_grounding | 68% [49%–87%] | 52% [33%–78%] | 96% [82%–100%] | 83% [64%–97%] | 100% [100%–100%] | 86% [70%–100%] | 40% [0%–100%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_code_dates | 68% [49%–87%] | 52% [33%–78%] | 96% [82%–100%] | 74% [42%–97%] | 100% [100%–100%] | 77% [44%–100%] | 40% [0%–100%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_pass2 | 68% [49%–87%] | 52% [33%–78%] | 96% [82%–100%] | 83% [64%–97%] | 100% [100%–100%] | 86% [70%–100%] | 40% [0%–100%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |

### Difference vs `baseline` (paired bootstrap; if the interval includes 0, treat as noise)

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| full | -4.2 [-14.5, +7.8] | -3.7 [-12.9, +13.5] | -4.3 [-18.2, +0.0] | +21.7 [-26.7, +64.3] | +0.0 [+0.0, +0.0] | -9.3 [-26.1, +0.0] | +17.1 [-32.4, +81.4] | -100.0 [-100.0, -100.0] | – | +0.0 [+0.0, +0.0] |
| no_grounding | -4.2 [-14.5, +7.8] | -3.7 [-12.9, +13.5] | -4.3 [-18.2, +0.0] | +21.7 [-26.7, +64.3] | +0.0 [+0.0, +0.0] | -9.3 [-26.1, +0.0] | +17.1 [-32.4, +81.4] | -100.0 [-100.0, -100.0] | – | +0.0 [+0.0, +0.0] |
| no_code_dates | -4.2 [-14.5, +7.8] | -3.7 [-12.9, +13.5] | -4.3 [-18.2, +0.0] | +13.0 [-47.6, +63.3] | +0.0 [+0.0, +0.0] | -18.4 [-52.2, +0.0] | +17.1 [-32.4, +81.4] | -100.0 [-100.0, -100.0] | – | +0.0 [+0.0, +0.0] |
| no_pass2 | -4.2 [-14.5, +7.8] | -3.7 [-12.9, +13.5] | -4.3 [-18.2, +0.0] | +21.7 [-26.7, +64.3] | +0.0 [+0.0, +0.0] | -9.3 [-26.1, +0.0] | +17.1 [-32.4, +81.4] | -100.0 [-100.0, -100.0] | – | +0.0 [+0.0, +0.0] |

### Ablations: held-out test, groq

Matcher: **turns**. Values are micro-averaged over 10 meetings; brackets are 95% bootstrap CIs over meetings.

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| full | 68% [49%–87%] | 52% [33%–78%] | 96% [82%–100%] | 83% [64%–97%] | 100% [100%–100%] | 86% [70%–100%] | 0% [0%–0%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_grounding | 68% [49%–87%] | 52% [33%–78%] | 96% [82%–100%] | 83% [64%–97%] | 100% [100%–100%] | 86% [70%–100%] | 0% [0%–0%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_code_dates | 68% [49%–87%] | 52% [33%–78%] | 96% [82%–100%] | 74% [42%–97%] | 100% [100%–100%] | 77% [44%–100%] | 0% [0%–0%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_pass2 | 68% [49%–87%] | 52% [33%–78%] | 96% [82%–100%] | 83% [64%–97%] | 100% [100%–100%] | 86% [70%–100%] | 0% [0%–0%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |

### Difference vs `full` (paired bootstrap; if the interval includes 0, treat as noise)

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| no_grounding | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| no_code_dates | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | -8.7 [-25.0, +0.0] | +0.0 [+0.0, +0.0] | -9.1 [-26.1, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| no_pass2 | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |

### Dev vs test (full pipeline)

| metric | dev | test [95% CI] |
|---|---|---|
| Action F1 | 44% | 68% [49%–87%] |
| Action precision | 35% | 52% [33%–78%] |
| Action recall | 60% | 96% [82%–100%] |
| Fully-correct actions (recall) | 60% | 83% [64%–97%] |
| Owner accuracy | 100% | 100% [100%–100%] |
| Deadline accuracy | 100% | 86% [70%–100%] |
| Decision F1 | 0% | 0% [0%–0%] |
| Unresolved-question recall | 50% | 0% [0%–0%] |
| Ungrounded items in output | 0% | 0% [0%–0%] |
| Spurious actions / negative meeting | – | 0.0 [0.0–0.0] |
