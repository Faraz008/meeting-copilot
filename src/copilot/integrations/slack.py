import time

import httpx

from copilot.digest import MeetingDigest
from copilot.llm.base import RateLimited, TransientError
from copilot.llm.retry import with_retries


def esc(s: str) -> str:
    """Escape Slack control characters to prevent formatting and mention injection."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_payload(d: MeetingDigest) -> dict:
    def line(a) -> str:
        result = f"• {esc(a.title)}"

        if a.owner:
            result += f" — _{esc(a.owner)}_"

        if a.deadline:
            result += f" (due {a.deadline})"

        return result

    sections = []

    if d.decisions:
        decision_lines = [f"• {esc(x.title)}" for x in d.decisions]
        sections.append("*Decisions*\n" + "\n".join(decision_lines))

    if d.actions:
        sections.append("*Action items*\n" + "\n".join(line(a) for a in d.actions))

    if d.unowned:
        sections.append(":raising_hand: *Need an owner*\n" + "\n".join(line(a) for a in d.unowned))

    if d.questions:
        question_lines = [f"• {esc(q.title)}" for q in d.questions]
        sections.append(":question: *Open questions*\n" + "\n".join(question_lines))

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{d.title} ({d.date})"[:150],
            },
        }
    ]

    blocks.extend(
        [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": section[:2900],
                },
            }
            for section in sections[:40]
        ]
    )

    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"<{d.url}|Review in Co-Pilot>",
                }
            ],
        }
    )

    return {
        "text": f"Meeting summary: {d.title}",
        "blocks": blocks,
    }


def post(
    url: str,
    payload: dict,
    *,
    client: httpx.Client | None = None,
    sleep=time.sleep,
) -> None:
    c = client or httpx.Client(timeout=15)

    def once():
        try:
            r = c.post(url, json=payload)
        except httpx.TransportError as e:
            raise TransientError(type(e).__name__) from e

        if r.status_code == 429:
            raise RateLimited(retry_after=float(r.headers.get("retry-after", 2)))

        if r.status_code >= 500:
            raise TransientError(f"http {r.status_code}")

        r.raise_for_status()

    with_retries(once, sleep=sleep)
