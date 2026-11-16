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
    )
]


def redact(s: str) -> str:
    for k in (settings.groq_api_key, settings.gemini_api_key, settings.openrouter_api_key):
        if k and len(k) > 8:
            s = s.replace(k, "[REDACTED]")
    for p in PATTERNS:
        s = p.sub("[REDACTED]", s)
    return s
