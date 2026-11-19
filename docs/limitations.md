

# Limitations

## Measured on a small benchmark

The evaluation uses:

- **5 development meetings** (`s01`–`s05`).
- **10 held-out test meetings** (`s06`–`s15`).
- **23 gold action items** in the held-out test split.

Gold annotations were written by one person, with self-agreement checks. There was no independent second annotator, so inter-annotator agreement has not been established.

The test results use 95% bootstrap confidence intervals over only 10 meetings. These intervals can be wide, and a small number of meetings can substantially affect the aggregate metrics. The results should be treated as an evaluation of this benchmark, not a reliable estimate of performance across arbitrary business meetings.

## Synthetic-heavy data

The held-out test set contains **10 synthetic meetings and 0 real meetings**.

Although 10 real AMI meeting transcripts were collected for exploration, they were not included in the scored held-out test set.

Consequently, the reported Action F1, owner accuracy and deadline accuracy primarily measure performance on structured synthetic transcripts. They do not establish equivalent performance on naturally occurring workplace conversations, with interruptions, incomplete sentences, overlapping speech or inconsistent speaker labels.

Real-meeting generalization remains unverified.

## Per-failure-class notes

The evaluation error taxonomy distinguishes several types of extraction errors. Examples of categories include:

| Failure class | What the evaluator distinguishes |
|---|---|
| Missed commitments | A committed action was not extracted (`action:missed_commitment`). |
| Missed proposals | A proposed action was not extracted (`action:missed_proposal`). |
| Missed revisions | An action involving a retraction or revision was missed (`action:missed_revision_case`). |
| Duplicate or split actions | One gold action was represented by duplicate or fragmented predictions (`action:duplicate_or_split`). |
| Past-tense false positives | A completed action was incorrectly extracted as a current action (`action:past_tense_extracted`). |
| Ambiguous ownership | The owner was left unresolved and flagged (`owner:ambiguous_flagged`). |
| Incorrect ownership | An owner was missed, invented or assigned to the wrong person. |
| Unresolved deadlines | A deadline could not be resolved and was flagged (`deadline:unresolvable_flagged`). |
| Incorrect deadlines | A deadline was missing, invented, assigned the wrong value or selected incorrectly from ambiguous options. |

These categories describe the evaluator's error classification, not a claim that every category occurred in every provider run. The generated error reports contain the individual mismatches and should be consulted for actual counts.

The taxonomy also depends on the matching strategy. Title-based matching and turn-based matching can classify the same extraction differently.

## Free-tier model dependence

Results are specific to the models and configurations used during evaluation.

The final provider configurations included:

- Groq: `openai/gpt-oss-120b`
- OpenRouter: `nvidia/nemotron-3-ultra-550b-a55b:free`
- Ollama: `qwen3:4b`

Free-tier model availability, routing, rate limits and model behavior can change without notice. Repeating an evaluation against a provider later may therefore produce different outputs, even when the application code is unchanged.

The replay cache preserves recorded LLM responses for deterministic regression testing. It makes replay independent of live provider availability, but it does not guarantee that a future live model will behave identically.

## Language, dates and timezones

- The extraction and evaluation workflow is designed for English transcripts.
- Non-English and multilingual meeting performance has not been established.
- The default date interpretation order is **DMY**.
- Each meeting uses one configured timezone.
- Mixed timezones within a meeting and speaker-specific timezone interpretation are not supported as separate evaluation cases.

Ambiguous dates and relative deadlines can therefore remain unresolved or be interpreted incorrectly.

## Names are not redacted

The `--redact` option removes supported identifier patterns, including email addresses, phone numbers and other configured identifiers.

**Person names are not redacted.** They are needed for speaker and action-item owner resolution.

As a result, cloud-provider mode can still send participant names and other contextual personal information contained in transcripts. Identifier redaction should not be treated as complete anonymization or as a guarantee that a transcript contains no personal data.

Use local-only mode when transcript content must not be sent to an external LLM provider.

## Audio and diarization

Audio ingestion and diarization were optional and were not implemented in this project.

The current workflow operates on text transcripts with speaker labels. It does not process raw audio, identify speakers from voice characteristics or correct diarization errors.

Therefore, the reported owner-accuracy metrics apply to the supplied transcript speaker labels and owner-resolution pipeline. They do not measure audio-based speaker identification accuracy.

## Replay CI limitations

The replay CI job uses recorded LLM responses rather than making live model calls.

It verifies that application changes do not break the deterministic extraction path for the recorded inputs. An intentional extraction fault that removed all predicted actions caused the replay evaluation gate to fail.

However, replay CI cannot establish whether a modified prompt produces better or worse responses from a live model. It does not independently evaluate prompt quality, model drift or behavior on unseen conversations.

A passing replay test is evidence of regression resistance against the recorded fixtures, not proof of live-provider quality.

## Authentication, multi-user support and storage security

The current Streamlit application has no authentication or user-account system.

- There is no login or role-based access control.
- The application does not provide tenant isolation or a multi-user permission model.
- Local SQLite storage is not encrypted at rest.
- Transcript and extracted meeting data are not protected by an application-level encryption layer.

The application should be treated as a local development prototype rather than a production-ready multi-user system for confidential meeting data.
