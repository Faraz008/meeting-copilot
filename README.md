# meeting-copilot

## Replay Regression Test

Verified that the CI replay evaluation gate detects extraction regressions using recorded LLM responses.

For the test, I temporarily introduced an intentional fault in `src/copilot/eval/runner.py`:

```python
pred.actions = []
```

This caused all six replay meetings to produce zero actions.

The `eval-replay` CI job correctly failed on the following metrics:

- `act_f1`: 0.000 (required ≥ 0.558)
- `act_r`: 0.000 (required ≥ 0.970)
- `act_full_recall`: 0.000 (required ≥ 0.970)

The regression was tested on a temporary scratch branch and was not merged.

### CI failure evidence

![Replay regression detected by GitHub Actions](docs/images/replay-regression-failure.png)
