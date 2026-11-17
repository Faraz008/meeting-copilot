import hashlib
import re
import smtplib
import ssl
import time
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment

from copilot.digest import MeetingDigest
from copilot.integrations.directory import Directory
from copilot.integrations.ics import build_ics
from copilot.store import Store

HTML = Environment(
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

TEXT = Environment(
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


_BODY = r"""
{% macro due(a) %}
{% if a.deadline %}
(due {{ a.deadline }}{% if a.deadline_time %}
{{ a.deadline_time.strftime('%H:%M') }}{% endif %}
{% if 'ambiguous_deadline' in a.flags %},
please confirm the date{% endif %})
{% endif %}
{% endmacro %}
"""


TEXT_T = TEXT.from_string(
    _BODY
    + """
Hi {{ name }},

Summary of "{{ d.title }}" ({{ d.date }}).
{% if mine %}

YOUR ACTION ITEMS
{% for a in mine %}
- {{ a.title }}{{ due(a) }}
{% endfor %}
{% endif %}
{% if d.decisions %}

DECISIONS
{% for x in d.decisions %}
- {{ x.title }}
{% endfor %}
{% endif %}
{% if d.by_owner() %}

ALL ACTION ITEMS
{% for owner, acts in d.by_owner().items() %}
{{ owner }}:
{% for a in acts %}
- {{ a.title }}{{ due(a) }}
{% endfor %}
{% endfor %}
{% endif %}
{% if d.unowned %}

STILL NEEDS AN OWNER
{% for a in d.unowned %}
- {{ a.title }}
{% endfor %}
{% endif %}
{% if d.questions %}

OPEN QUESTIONS
{% for q in d.questions %}
- {{ q.title }}
{% endfor %}
{% endif %}

Something wrong? Review it here: {{ d.url }}
"""
)


HTML_T = HTML.from_string(
    _BODY
    + """
<p>Hi {{ name }},</p>

<p>
    Summary of <b>{{ d.title }}</b> ({{ d.date }}).
</p>

{% if mine %}
<h3>Your action items</h3>
<ul>
    {% for a in mine %}
    <li>{{ a.title }}{{ due(a) }}</li>
    {% endfor %}
</ul>
{% endif %}

{% if d.decisions %}
<h3>Decisions</h3>
<ul>
    {% for x in d.decisions %}
    <li>{{ x.title }}</li>
    {% endfor %}
</ul>
{% endif %}

{% if d.by_owner() %}
<h3>All action items</h3>
{% for owner, acts in d.by_owner().items() %}
<b>{{ owner }}</b>
<ul>
    {% for a in acts %}
    <li>{{ a.title }}{{ due(a) }}</li>
    {% endfor %}
</ul>
{% endfor %}
{% endif %}

{% if d.unowned %}
<h3>Still needs an owner</h3>
<ul>
    {% for a in d.unowned %}
    <li>{{ a.title }}</li>
    {% endfor %}
</ul>
{% endif %}

{% if d.questions %}
<h3>Open questions</h3>
<ul>
    {% for q in d.questions %}
    <li>{{ q.title }}</li>
    {% endfor %}
</ul>
{% endif %}

<p>
    <a href="{{ d.url }}">Review in Co-Pilot</a>
</p>
"""
)


@dataclass
class EmailPlan:
    name: str
    to: str | None
    subject: str
    text: str
    html: str
    ics: bytes | None = None
    skip: str | None = None


def plan_emails(
    d: MeetingDigest,
    directory: Directory,
) -> list[EmailPlan]:
    plans = []

    subject = re.sub(
        r"[\r\n]+",
        " ",
        f"Meeting summary: {d.title} ({d.date})",
    )[:200]

    for person in d.roster:
        addr = directory.email(person)

        if not addr:
            plans.append(
                EmailPlan(
                    person,
                    None,
                    subject,
                    "",
                    "",
                    skip=f"no email for {person} in roster.json",
                )
            )
            continue

        mine = d.by_owner().get(person, [])

        ctx = {
            "name": person,
            "d": d,
            "mine": mine,
        }

        ics = build_ics(mine) if any(action.deadline for action in mine) else None

        plans.append(
            EmailPlan(
                name=person,
                to=addr,
                subject=subject,
                text=TEXT_T.render(**ctx),
                html=HTML_T.render(**ctx),
                ics=ics,
            )
        )

    return plans


def build_message(
    p: EmailPlan,
    sender: str,
) -> EmailMessage:
    msg = EmailMessage()

    # EmailMessage rejects invalid header values.
    msg["From"] = sender
    msg["To"] = p.to
    msg["Subject"] = p.subject

    msg.set_content(p.text)
    msg.add_alternative(p.html, subtype="html")

    if p.ics:
        msg.add_attachment(
            p.ics,
            maintype="text",
            subtype="calendar",
            filename="deadlines.ics",
        )

    return msg


def _connect(
    host,
    port,
    user,
    password,
    factory=None,
):
    cls = factory or (smtplib.SMTP_SSL if port == 465 else smtplib.SMTP)

    conn = cls(host, port, timeout=30)

    if port != 465:
        conn.ehlo()

        if conn.has_extn("starttls"):
            conn.starttls(context=ssl.create_default_context())
            conn.ehlo()

    if user:
        conn.login(user, password or "")

    return conn


def deliver(
    plans: list[EmailPlan],
    store: Store,
    mid: str,
    *,
    sender: str,
    send: bool = False,
    force: bool = False,
    host: str | None = None,
    port: int = 587,
    user: str | None = None,
    password: str | None = None,
    outbox: str = "data/outbox",
    rate_per_min: float = 20,
    smtp_factory=None,
    sleep=time.sleep,
) -> list[dict]:
    """Dry-run by default: writes .eml files instead of sending."""

    results = []
    conn = None

    try:
        for p in plans:
            if p.skip:
                results.append(
                    {
                        "to": p.name,
                        "status": "skipped",
                        "detail": p.skip,
                    }
                )
                continue

            fp = hashlib.sha256((p.subject + p.text).encode()).hexdigest()

            rec = store.get_push(
                f"meeting:{mid}",
                f"email:{p.to}",
            )

            if rec and rec["status"] == "ok" and rec["payload_hash"] == fp and not force:
                results.append(
                    {
                        "to": p.to,
                        "status": "unchanged",
                    }
                )
                continue

            msg = build_message(p, sender)

            if not send:
                safe_to = re.sub(
                    r"[^a-zA-Z0-9.@-]",
                    "_",
                    p.to,
                )

                path = Path(outbox) / f"{mid}_{safe_to}.eml"

                path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                path.write_bytes(bytes(msg))

                results.append(
                    {
                        "to": p.to,
                        "status": "dry_run",
                        "detail": str(path),
                    }
                )
                continue

            try:
                conn = conn or _connect(
                    host,
                    port,
                    user,
                    password,
                    smtp_factory,
                )

                conn.send_message(msg)

                store.record_push(
                    f"meeting:{mid}",
                    f"email:{p.to}",
                    None,
                    None,
                    fp,
                    "ok",
                )

                results.append(
                    {
                        "to": p.to,
                        "status": "sent",
                    }
                )

                sleep(60 / rate_per_min)

            except (smtplib.SMTPException, OSError) as e:
                store.record_push(
                    f"meeting:{mid}",
                    f"email:{p.to}",
                    None,
                    None,
                    fp,
                    "failed",
                    str(e)[:200],
                )

                results.append(
                    {
                        "to": p.to,
                        "status": "failed",
                        "detail": type(e).__name__,
                    }
                )

    finally:
        if conn:
            try:
                conn.quit()
            except Exception:
                pass

    return results
