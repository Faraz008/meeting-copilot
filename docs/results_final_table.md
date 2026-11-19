### Baseline vs pipeline: held-out test, ollama

Matcher: **title**. Values are micro-averaged over 10 meetings; brackets are 95% bootstrap CIs over meetings.

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 68% [53%–82%] | 63% [48%–87%] | 74% [48%–100%] | 52% [21%–89%] | 94% [79%–100%] | 82% [59%–100%] | 20% [6%–38%] | 100% [100%–100%] | – | 0.0 [0.0–0.0] |
| full | 68% [48%–85%] | 54% [33%–77%] | 91% [71%–100%] | 65% [39%–88%] | 95% [82%–100%] | 81% [56%–100%] | 62% [20%–88%] | 100% [100%–100%] | 0% [0%–0%] | 7.0 [7.0–7.0] |
| no_grounding | 68% [48%–85%] | 54% [33%–77%] | 91% [71%–100%] | 65% [39%–88%] | 95% [82%–100%] | 81% [56%–100%] | 62% [20%–88%] | 100% [100%–100%] | 3% [0%–7%] | 7.0 [7.0–7.0] |
| no_code_dates | 68% [48%–85%] | 54% [33%–77%] | 91% [71%–100%] | 61% [29%–88%] | 95% [82%–100%] | 76% [43%–100%] | 62% [20%–88%] | 100% [100%–100%] | 0% [0%–0%] | 7.0 [7.0–7.0] |
| no_pass2 | 67% [47%–84%] | 52% [33%–77%] | 91% [71%–100%] | 65% [39%–88%] | 95% [82%–100%] | 81% [56%–100%] | 62% [20%–88%] | 100% [100%–100%] | 0% [0%–0%] | 7.0 [7.0–7.0] |

### Difference vs `baseline` (paired bootstrap; if the interval includes 0, treat as noise)

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| full | -0.3 [-23.3, +20.5] | -9.1 [-33.7, +8.2] | +17.4 [+0.0, +42.9] | +13.0 [-35.3, +58.6] | +1.1 [-13.6, +20.0] | -1.4 [-33.3, +30.0] | +41.5 [+13.3, +57.9] | +0.0 [+0.0, +0.0] | – | +7.0 [+7.0, +7.0] |
| no_grounding | -0.3 [-23.3, +20.5] | -9.1 [-33.7, +8.2] | +17.4 [+0.0, +42.9] | +13.0 [-35.3, +58.6] | +1.1 [-13.6, +20.0] | -1.4 [-33.3, +30.0] | +41.5 [+13.3, +57.9] | +0.0 [+0.0, +0.0] | – | +7.0 [+7.0, +7.0] |
| no_code_dates | -0.3 [-23.3, +20.5] | -9.1 [-33.7, +8.2] | +17.4 [+0.0, +42.9] | +8.7 [-45.8, +57.9] | +1.1 [-13.6, +20.0] | -6.2 [-46.2, +30.0] | +41.5 [+13.3, +57.9] | +0.0 [+0.0, +0.0] | – | +7.0 [+7.0, +7.0] |
| no_pass2 | -1.3 [-24.6, +19.0] | -10.5 [-34.2, +6.3] | +17.4 [+0.0, +42.9] | +13.0 [-35.3, +58.6] | +1.1 [-13.6, +20.0] | -1.4 [-33.3, +30.0] | +41.5 [+13.3, +57.9] | +0.0 [+0.0, +0.0] | – | +7.0 [+7.0, +7.0] |

### Ablations: held-out test, ollama

Matcher: **turns**. Values are micro-averaged over 10 meetings; brackets are 95% bootstrap CIs over meetings.

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| full | 61% [38%–79%] | 49% [27%–72%] | 83% [59%–100%] | 65% [40%–88%] | 100% [100%–100%] | 79% [50%–100%] | 46% [14%–78%] | 100% [100%–100%] | 0% [0%–0%] | 7.0 [7.0–7.0] |
| no_grounding | 61% [38%–79%] | 49% [27%–72%] | 83% [59%–100%] | 65% [40%–88%] | 100% [100%–100%] | 79% [50%–100%] | 46% [14%–78%] | 100% [100%–100%] | 3% [0%–7%] | 7.0 [7.0–7.0] |
| no_code_dates | 61% [38%–79%] | 49% [27%–72%] | 83% [59%–100%] | 61% [29%–88%] | 100% [100%–100%] | 74% [37%–100%] | 46% [14%–78%] | 100% [100%–100%] | 0% [0%–0%] | 7.0 [7.0–7.0] |
| no_pass2 | 60% [38%–79%] | 48% [26%–72%] | 83% [59%–100%] | 65% [40%–88%] | 100% [100%–100%] | 79% [50%–100%] | 46% [14%–78%] | 100% [100%–100%] | 0% [0%–0%] | 7.0 [7.0–7.0] |

### Difference vs `full` (paired bootstrap; if the interval includes 0, treat as noise)

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| no_grounding | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +3.2 [+0.0, +7.4] | +0.0 [+0.0, +0.0] |
| no_code_dates | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | -4.3 [-12.5, +0.0] | +0.0 [+0.0, +0.0] | -5.3 [-14.8, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| no_pass2 | -1.0 [-3.2, +0.0] | -1.2 [-3.9, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |

### Dev vs test (full pipeline)

| metric | dev | test [95% CI] |
|---|---|---|
| Action F1 | 0% | 61% [38%–79%] |
| Action precision | – | 49% [27%–72%] |
| Action recall | 0% | 83% [59%–100%] |
| Fully-correct actions (recall) | 0% | 65% [40%–88%] |
| Owner accuracy | – | 100% [100%–100%] |
| Deadline accuracy | – | 79% [50%–100%] |
| Decision F1 | – | 46% [14%–78%] |
| Unresolved-question recall | 0% | 100% [100%–100%] |
| Ungrounded items in output | – | 0% [0%–0%] |
| Spurious actions / negative meeting | – | 7.0 [7.0–7.0] |
