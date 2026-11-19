### Baseline vs pipeline: held-out test, openrouter

Matcher: **title**. Values are micro-averaged over 10 meetings; brackets are 95% bootstrap CIs over meetings.

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 65% [46%–79%] | 51% [35%–70%] | 87% [57%–100%] | 48% [17%–82%] | 95% [79%–100%] | 85% [62%–100%] | 16% [4%–28%] | 100% [100%–100%] | – | 0.0 [0.0–0.0] |
| full | 23% [12%–30%] | 19% [15%–30%] | 30% [9%–65%] | 22% [3%–56%] | 71% [17%–100%] | 100% [100%–100%] | 8% [0%–31%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_grounding | 23% [12%–30%] | 19% [15%–30%] | 30% [9%–65%] | 22% [3%–56%] | 71% [17%–100%] | 100% [100%–100%] | 8% [0%–31%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_code_dates | 23% [12%–30%] | 19% [15%–30%] | 30% [9%–65%] | 22% [3%–56%] | 71% [17%–100%] | 100% [100%–100%] | 8% [0%–31%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_pass2 | 23% [12%–29%] | 18% [14%–30%] | 30% [9%–65%] | 22% [3%–56%] | 71% [17%–100%] | 100% [100%–100%] | 8% [0%–27%] | 100% [100%–100%] | 0% [0%–0%] | 0.0 [0.0–0.0] |

### Difference vs `baseline` (paired bootstrap; if the interval includes 0, treat as noise)

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| full | -41.2 [-58.4, -23.8] | -32.4 [-48.5, -16.9] | -56.5 [-82.8, -21.4] | -26.1 [-61.5, +7.7] | -23.6 [-76.2, +0.0] | +15.0 [+0.0, +38.5] | -7.4 [-21.7, +12.5] | -100.0 [-100.0, -100.0] | – | +0.0 [+0.0, +0.0] |
| no_grounding | -41.2 [-58.4, -23.8] | -32.4 [-48.5, -16.9] | -56.5 [-82.8, -21.4] | -26.1 [-61.5, +7.7] | -23.6 [-76.2, +0.0] | +15.0 [+0.0, +38.5] | -7.4 [-21.7, +12.5] | -100.0 [-100.0, -100.0] | – | +0.0 [+0.0, +0.0] |
| no_code_dates | -41.2 [-58.4, -23.8] | -32.4 [-48.5, -16.9] | -56.5 [-82.8, -21.4] | -26.1 [-61.5, +7.7] | -23.6 [-76.2, +0.0] | +15.0 [+0.0, +38.5] | -7.4 [-21.7, +12.5] | -100.0 [-100.0, -100.0] | – | +0.0 [+0.0, +0.0] |
| no_pass2 | -41.6 [-58.4, -24.8] | -32.9 [-48.5, -17.9] | -56.5 [-82.8, -21.4] | -26.1 [-61.5, +7.7] | -23.6 [-76.2, +0.0] | +15.0 [+0.0, +38.5] | -7.7 [-21.7, +8.7] | +0.0 [+0.0, +0.0] | – | +0.0 [+0.0, +0.0] |

### Ablations: held-out test, openrouter

Matcher: **turns**. Values are micro-averaged over 10 meetings; brackets are 95% bootstrap CIs over meetings.

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| full | 20% [7%–27%] | 16% [12%–20%] | 26% [5%–64%] | 22% [3%–56%] | 83% [33%–100%] | 100% [100%–100%] | 8% [0%–31%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_grounding | 20% [7%–27%] | 16% [12%–20%] | 26% [5%–64%] | 22% [3%–56%] | 83% [33%–100%] | 100% [100%–100%] | 8% [0%–31%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_code_dates | 20% [7%–27%] | 16% [12%–20%] | 26% [5%–64%] | 22% [3%–56%] | 83% [33%–100%] | 100% [100%–100%] | 8% [0%–31%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |
| no_pass2 | 20% [7%–27%] | 16% [12%–20%] | 26% [5%–64%] | 22% [3%–56%] | 83% [33%–100%] | 100% [100%–100%] | 8% [0%–27%] | 0% [0%–0%] | 0% [0%–0%] | 0.0 [0.0–0.0] |

### Difference vs `full` (paired bootstrap; if the interval includes 0, treat as noise)

| system | Action F1 | Action precision | Action recall | Fully-correct actions (recall) | Owner accuracy | Deadline accuracy | Decision F1 | Unresolved-question recall | Ungrounded items in output | Spurious actions / negative meeting |
|---|---|---|---|---|---|---|---|---|---|---|
| no_grounding | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| no_code_dates | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| no_pass2 | -0.3 [-1.1, +0.0] | -0.4 [-1.5, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | -0.3 [-4.1, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |

### Dev vs test (full pipeline)

| metric | dev | test [95% CI] |
|---|---|---|
| Action F1 | 0% | 20% [7%–27%] |
| Action precision | – | 16% [12%–20%] |
| Action recall | 0% | 26% [5%–64%] |
| Fully-correct actions (recall) | 0% | 22% [3%–56%] |
| Owner accuracy | – | 83% [33%–100%] |
| Deadline accuracy | – | 100% [100%–100%] |
| Decision F1 | – | 8% [0%–31%] |
| Unresolved-question recall | 0% | 0% [0%–0%] |
| Ungrounded items in output | – | 0% [0%–0%] |
| Spurious actions / negative meeting | – | 0.0 [0.0–0.0] |
