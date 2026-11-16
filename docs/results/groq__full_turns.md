# groq__full

matcher: **turns** · meetings: 6 · gold actions: 10 · predicted actions: 24
system: pipeline · models: [['groq', 'openai/gpt-oss-120b']] · git: {'sha': 'da00bac', 'dirty': True} · prompt sha: da88522e

| metric | value [95% CI over meetings] |
|---|---|
| Action F1 | 59% [48%–68%] |
| Action precision | 42% [32%–52%] |
| Action recall | 100% [100%–100%] |
| Fully-correct actions (recall) | 100% [100%–100%] |
| Owner accuracy | 100% [100%–100%] |
| Deadline accuracy | 100% [100%–100%] |
| Deadline (ambiguity-lenient) | 100% [100%–100%] |
| Status accuracy | 100% [100%–100%] |
| Decision F1 | 0% [0%–0%] |
| Question F1 | 60% [0%–83%] |
| Unresolved-question recall | 100% [100%–100%] |
| Unresolved-question precision | 50% [0%–100%] |
| Ungrounded items in output | 0% [0%–0%] |
| Raw hallucination rate (pre-filter) | 0% [0%–0%] |
| Spurious actions / negative meeting | – |
| Schema/JSON failure rate | 0% [0%–0%] |
| Repairs / meeting | 0.0 [0.0–0.0] |
| Incomplete runs | 0% [0%–0%] |

Deadline errors on matched actions: missing 0, invented 0, wrong value 0.

## Hard cases (per tag)

| tag | n | found | fully correct |
|---|---|---|---|
| deferred | 1 | 0/1 | 0/1 |
| no_deadline | 7 | 7/7 | 7/7 |
| no_owner | 4 | 4/4 | 4/4 |
| proposed | 4 | 4/4 | 4/4 |
| relative_date | 1 | 1/1 | 1/1 |
| retraction | 1 | 1/1 | 1/1 |
| revision | 2 | 2/2 | 2/2 |
| unanswered | 1 | 1/1 | 1/1 |

## Per meeting

| meeting | actions TP/FP/FN | decisions TP/FP/FN | questions TP/FP/FN | mismatches |
|---|---|---|---|---|
| m001 | 1/1/0 | 0/1/0 | 1/0/0 | 0 |
| s01 | 1/2/0 | 0/1/0 | 0/1/0 | 0 |
| s02 | 1/3/0 | 0/1/0 | 0/1/0 | 0 |
| s03 | 4/3/0 | 0/0/0 | 0/1/0 | 0 |
| s04 | 1/2/0 | 0/0/0 | 2/1/0 | 0 |
| s05 | 2/3/0 | 0/1/0 | 0/0/0 | 0 |
