# Provider Reconnaissance

Date: 13 November 2026

Method:
- Sequential: 3 requests, followed by 5 requests per provider.
- Burst: 30 concurrent requests per hosted provider using the same synthetic transcript.
- Long transcript: 1 request per hosted provider.
- Local: 1 additional Ollama request.

## Results

| Provider | Model | Success rate | Median latency (burst) | JSON fenced | Errors observed | Rate limit observed | owner_raw |
|---|---|---:|---:|---:|---|---|---|
| Groq | `openai/gpt-oss-120b` | 12/39 (30.8%) | 1.27 s | 0 | HTTP 429, bad JSON | Yes; Retry-After: 5 s | 0/4 |
| OpenRouter | `nvidia/nemotron-3-ultra-550b-a55b:free` | 38/39 (97.4%) | 7.52 s | 0 | Empty response | No 429 observed | 30/30 |
| Ollama | `qwen3:4b` | 0/9 (0%) | N/A | 0 | ReadTimeout, empty response | Not tested | N/A |
| Gemini | `gemini-3.8-flash` | 0/39 (0%) | 1.05 s | 0 | HTTP 429, HTTP 503, timeout | Yes; HTTP 429 | N/A |

Note:
- Success rate combines all requests across the listed tests.
- Burst median latency is reported for hosted providers. Ollama was not included in the burst test.
- JSON fencing was not observed in any reported run.
- `owner_raw` was checked only on responses that passed the script's JSON validation. `N/A` means no valid response was available for checking.
- Rate-limit observations describe responses encountered during testing, not the providers' published quota limits.

## Current observations

- Groq was fast but unreliable under concurrent load, with rate limits and malformed JSON.
- Gemini failed across the completed tests due to service errors, rate limits and timeouts.
- OpenRouter had the highest observed success rate and passed all 30 burst owner checks, but returned an empty response on the long transcript.
- Ollama experienced timeouts in sequential testing and an empty response in the local test.
- OpenRouter is the strongest current candidate, but long-transcript reliability still needs investigation.

## Retry-design implications

- HTTP 429: honor `Retry-After`; use bounded exponential backoff with jitter.
- HTTP 503: retry a limited number of times with backoff.
- Network timeout: use bounded retries and provider-specific timeouts.
- Empty response: classify separately and inspect before fallback.
- Bad JSON: allow at most one controlled repair attempt before fallback.
- Owner mismatch: treat as an extraction-quality failure, not a transport failure.
- Use provider-specific concurrency limits and maintain a fallback provider.
