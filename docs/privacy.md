# Privacy and Data Handling

## LLM Processing Modes

The following table describes what is sent to LLM providers and what is stored locally in each mode.

| Mode | LLM calls | What is sent | What is stored locally |
|---|---|---|---|
| Default | Cloud providers | Transcript chunks | Transcript and items in `data/copilot.sqlite` |
| `--redact` | Cloud providers | Transcript chunks with identifiers tokenized. Person names are **not** hidden. | Same as default, including original text |
| `--local-only` | Ollama on localhost | Nothing leaves the machine | Transcript and items in `data/copilot.sqlite` |

## External Integrations

Pushes to Notion, Jira, email, and Slack are separate, explicit actions performed after review. They are not automatic consequences of LLM processing.

## Data Deletion

Use the following command to delete a meeting and its associated items:

```bash
copilot purge <id>
```
