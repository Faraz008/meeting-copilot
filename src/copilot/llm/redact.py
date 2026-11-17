import re

from copilot.config import settings

PATTERNS = [
    re.compile(p)
    for p in (
        r"gsk_[A-Za-z0-9]{20,}",
        r"AIza[0-9A-Za-z_\-]{30,}",
        r"sk-or-[A-Za-z0-9\-_]{20,}",
        r"Bearer\s+[A-Za-z0-9._\-]{16,}",
        r"(?:ntn|secret)_[A-Za-z0-9]{20,}",
        r"hf_[A-Za-z0-9]{20,}",
        r"https://hooks\.slack\.com/services/[A-Za-z0-9/]+",
    )
]


def _secrets() -> list[str | None]:
    s = settings
    return [
        s.groq_api_key,
        s.gemini_api_key,
        s.openrouter_api_key,
        s.notion_token,
        s.jira_api_token,
        s.smtp_password,
        s.slack_webhook_url,
        s.hf_token,
        s.api_key,
    ]


def redact(s: str) -> str:
    for k in _secrets():
        if k and len(k) > 8:
            s = s.replace(k, "[REDACTED]")
    for p in PATTERNS:
        s = p.sub("[REDACTED]", s)
    return s
