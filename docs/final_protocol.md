# Final Evaluation Protocol

**Protocol date:** 2026-11-17
**Frozen Git tag:** `v0.9.1-frozen`
**Frozen commit SHA:** d62602667877fb3385119f8018e816d84665e8bd
**Previous freeze:** `v0.9-frozen` (preserved; not moved or deleted)

## 1. Test split

- **Location:** `data/gold/test`
- **Meetings:** 10 (`s06`–`s15`)
- **Gold action items:** 23
- **Composition:** 10 synthetic, 0 real
- **Integrity manifest:** `data/SPLITS.sha256.json`
- **Split integrity:** Must pass `python scripts/split_integrity.py` before evaluation.

The test split is held out. Test transcripts and labels must not be used for prompt development, threshold tuning, resolver changes, or debugging.

## 2. Frozen pipeline configuration

- **Extraction prompt:** `prompts/extract_v2.md`
- **Prompt SHA-256:** f7061c7f1fcb8ffc1f9c92ed2e24da388bb366b2e9152dddade9b52c2971ad34
- **Thresholds:** Default configuration; no documented threshold overrides.
- **Resolver rules:** Frozen at the tagged commit.
- **Gold labels:** Frozen at the tagged commit.
- **Matcher implementation:** Frozen at the tagged commit.

### Prompt leakage resolution

The initial leak check found an exact 8-gram overlap between `prompts/extract_v2.md` and the dev transcript `data/synthetic/s05.json`.

The prompt contained a transcript-specific ownership example. It was replaced with a generic ownership rule that preserves the intended extraction instruction without reproducing the transcript wording.

The leak check was subsequently rerun and reported:

`no prompt/transcript overlap`

The corrected prompt is included in `v0.9.1-frozen`. The original `v0.9-frozen` tag remains unchanged.

## 3. Providers and pinned models

Each provider is evaluated independently. Record the actual provider and model identifier used by every run.

| Provider | Pinned model |
|---|---|
| Groq | `openai/gpt-oss-120b` |
| Gemini | `gemini-3.8-flash` |
| OpenRouter | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| Ollama | `qwen3:4b` |

These identifiers must be verified against the configuration and actual run metadata before evaluation. No silent model substitutions are permitted.

If a provider or model is unavailable, record the infrastructure failure rather than substituting another model.

## 4. Systems evaluated per provider

Run the following systems independently for each available provider:

1. `baseline_v1`
2. `full`
3. `no_grounding`
4. `no_code_dates`
5. `no_pass2`

Each system must use the same frozen test split and its specified configuration.

## 5. Matchers

- **Title matcher:** Used for the `baseline_v1` versus `full` headline comparison.
- **Turn matcher:** Used for pipeline ablations (`no_grounding`, `no_code_dates`, `no_pass2`).

Matcher selection and implementation must remain unchanged after test evaluation begins.

## 6. Metrics

**Primary metric:**
- Action-item F1

**Secondary metrics:**
- Fully-correct action recall
- Owner accuracy
- Deadline accuracy
- Decision F1
- Unresolved-question recall
- Ungrounded rate
- Spurious actions per negative meeting

Report results separately for each provider and system. Include the number of evaluated meetings and relevant item counts alongside aggregate scores.

## 7. Uncertainty and statistical comparisons

- Report 95% bootstrap confidence intervals over meetings.
- Report paired bootstrap confidence intervals for ablation differences against `full`.
- Resample meetings rather than individual action items.
- Use the same bootstrap procedure for all compared systems.
- With only 10 test meetings, confidence intervals may be wide. Small differences should not be presented as conclusive evidence of superiority.

## 8. Single-run rule

- Each provider/system combination is run once.
- Infrastructure failures, such as provider outages or process termination, may be resumed using `--resume` if supported by the evaluation runner.
- Completed predictions must never be regenerated.
- Preserve raw predictions, logs, provider/model metadata, and evaluation outputs.
- Do not rerun a completed combination because its score is disappointing.
- The evaluation runner's `--resume` option skips existing prediction files
  regardless of whether they are complete or successful.
- Therefore, resuming does not automatically recover incomplete predictions.
  Such cases must be recorded as execution deviations.
- Original prediction files and evaluation outputs are preserved.

## 9. Expected failure modes

Predictions based on development evaluation and the known error categories:

1. **Action-item precision problems:** The earlier development evaluation achieved action recall of `1.000` but action F1 of `0.588`. This suggests false positives are a significant risk. Proposals, conditional statements, deferred tasks, and ownership assignments may be incorrectly classified as committed actions.

2. **Weak decision extraction:** The earlier development evaluation had decision F1 of `0.000`. Implicit decisions and indirect agreement may remain difficult to distinguish from discussion, proposals, or unresolved questions.

3. **Ambiguous evidence and normalization:** Cases involving ambiguous owners, ASR errors, relative dates, revisions, and unanswered questions may produce incorrect evidence, owner attribution, deadline normalization, or action/decision classification.

The earlier development scores were obtained before the prompt leakage correction and may have been inflated. They are historical reference values, not the corrected development baseline. Record the corrected development evaluation separately before interpreting these predictions.

After the test run, report how many of these three predicted failure modes were observed. Support each conclusion with saved predictions and concrete examples.

## 10. Rules after seeing test results

Only the following are permitted after the test results are revealed:

- Genuine bug fixes, documented separately and explicitly labeled **post-hoc**.
- Limitations and failure-mode analysis.
- Reproducibility or reporting fixes that do not alter frozen predictions.

The following are prohibited for the headline evaluation:

- Prompt changes
- Model substitutions or changes
- Threshold changes
- Resolver-rule changes
- Matcher changes
- Gold-label changes
- Regeneration of completed predictions

The headline results must use the original predictions generated by the frozen pipeline.

Any post-hoc corrected results must be reported separately and must never replace the original headline results.

## 11. Deviations

- The initial prompt leakage check detected an overlap with dev transcript `s05`.
- The transcript-specific example was replaced with a generic ownership rule.
- The subsequent leak check reported no prompt/transcript overlap.
- The corrected prompt is included in `v0.9.1-frozen`.
- The original `v0.9-frozen` tag remains unchanged.
- No test labels or transcripts were used to correct the prompt.
- Other deviations: `None at protocol time. Record any infrastructure failures or execution deviations here after evaluation.`
- **Groq:** Final evaluation completed across all five systems.
- **OpenRouter:** The full pipeline produced incomplete predictions for
  s07, s12, s13, s14, and s15. Resuming did not regenerate these files.
- **Ollama:** The baseline prediction for s14 failed with
  `StructuredFailure: ollama:schema; ollama:schema`.
- **Ollama pipeline variants:** Full, no_grounding, no_code_dates,
  and no_pass2 completed across all 10 meetings.
- The resume implementation skipped existing incomplete or failed
  predictions. These results are retained and are not silently replaced.

## 12. Caching and execution budget

- Final evaluations used live read-through caching.
- Cache directory: `data/llm_cache_test`.
- Cache implementation keys responses using the model, messages, JSON mode, temperature, and maximum token count.
- Identical requests across variants can reuse cached responses, reducing repeated provider calls.
- The cache contained 99 files (approximately 0.13 MB) after evaluation.
- The planned workload was five variants across 10 test meetings, with approximately three calls per meeting. Actual calls varied by provider and pipeline behavior.
- Actual API expenditure and cache-hit savings were not independently measured; the workload estimate must not be interpreted as measured cost.
