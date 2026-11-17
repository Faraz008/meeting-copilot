# Security

## Untrusted Input

- Meeting transcripts are treated as untrusted input.
- HTML and Markdown content is escaped before rendering in the UI.
- Slack mentions are neutralized to prevent unintended notifications.
- Jira text is inserted into ADF text nodes rather than interpreted as raw markup.
- Email HTML content is automatically escaped.
- `EmailMessage` rejects invalid header injection attempts.

## Prompt Injection and External Actions

- Transcript content may contain instructions, but these cannot directly trigger external side effects.
- LLM output is stored locally in the database for review.
- External pushes require human approval and an explicit confirmation click or the CLI `--apply` flag.
- Email sending and Slack posting are separate explicit actions.
- Recipients and integration targets come from local configuration, never from transcript instructions.

## Secrets

- API keys, tokens, and credentials are stored in `.env`.
- Secrets are redacted from logs and error strings.
- The CI secret scan blocks commits containing detected secrets.
- `.env` must not be committed to the repository.

## API Security

- API authentication uses key-based authentication with constant-time comparison.
- Request bodies are limited to 2 MB.
- Binding to a public address is refused unless an API key is configured.
- API error responses do not expose stack traces.

## Deployment

- Streamlit has no built-in authentication in this project.
- Do not expose the Streamlit interface publicly when using real meeting data.
- The Day 23 deployment uses `DEMO_MODE=true` and synthetic data only.

## Known Limitations

The following protections are not implemented:

- Encryption at rest for the SQLite database.
- Multi-user permissions and access control.
- Audit logging beyond the integration push table.

These limitations should be considered before using the application with sensitive production meeting data.
