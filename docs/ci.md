# CI Evaluation Gate

## CI jobs

The `test` job runs Ruff checks, formatting validation, secret scanning, pytest with coverage, and gold-data validation.

The `eval-replay` job runs after `test` passes. It evaluates the pipeline using recorded LLM responses from `tests/replay_cache/`, without making API calls.

Real transcripts that cannot be committed because of licensing restrictions are skipped by the loader when missing. CI therefore evaluates only the data available in the repository, while local runs can cover the full development dataset when those transcripts are available.

## Re-recording the cache

Prompt, chunking, or model changes can make the replay cache stale. CI then fails with `STALE REPLAY CACHE`.

Re-record locally using the accepted `extract_v1` prompt:

```bash
python -m copilot.eval.cli run --name rec --provider groq --prompt extract_v1 --cache live --freeze
```

Review the new evaluation results, then commit the updated replay cache and manifest.

## Thresholds

Thresholds are stored in `eval_thresholds.json`. To update them after an accepted improvement, run:

```bash
python scripts/ci_eval.py --write-thresholds
```

Review the generated values before committing. Thresholds should be tightened gradually as evaluation quality improves, not lowered simply to hide regressions.

## What replay evaluation proves

Replay evaluation catches code regressions in resolvers, reconciliation, evidence grounding, ID generation, the pipeline adapter, and scoring using fixed LLM outputs.

It does not prove that changed prompts produce better outputs, because replay uses previously recorded responses. Prompt changes require fresh live evaluation and cache recording.
