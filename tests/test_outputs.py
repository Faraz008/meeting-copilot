import json
import smtplib
from datetime import UTC, date, datetime, time

from icalendar import Calendar

from copilot.digest import build_digest, to_markdown
from copilot.integrations.base import PushItem
from copilot.integrations.directory import Directory
from copilot.integrations.emailer import deliver, plan_emails
from copilot.integrations.ics import build_ics
from copilot.integrations.slack import build_payload, esc
from copilot.store import Store
from tests.helpers import seed

NOW = datetime(2025, 3, 12, tzinfo=UTC)


def roster_file(tmp_path, emails=True):
    p = tmp_path / "roster.json"
    roster = (
        {
            "Priya": {"email": "priya@x.test"},
            "Sam": {"email": "sam@x.test"},
        }
        if emails
        else {}
    )
    p.write_text(json.dumps(roster))
    return str(p)


def test_digest_groups_by_owner_and_markdown(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    seed(s, 2)

    d = build_digest(
        s,
        "m1",
        Directory(roster_file(tmp_path)),
    )

    assert set(d.by_owner()) == {"Priya", "Sam"}
    assert "## Priya" in to_markdown(d)


def test_email_dry_run_writes_eml_and_escapes_html(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    seed(s)

    s.update_item(
        "act_1",
        edits={"title": "<script>alert(1)</script> ship"},
    )

    d = build_digest(
        s,
        "m1",
        Directory(roster_file(tmp_path)),
    )
    plans = plan_emails(
        d,
        Directory(roster_file(tmp_path)),
    )

    assert "<script>" not in plans[0].html
    assert "&lt;script&gt;" in plans[0].html

    out = deliver(
        plans,
        s,
        "m1",
        sender="a@b.test",
        outbox=str(tmp_path / "box"),
    )

    assert out[0]["status"] == "dry_run"
    assert any(r["status"] == "skipped" for r in out)  # Dan has no email

    assert list((tmp_path / "box").glob("*.eml"))


def test_email_send_is_idempotent_and_failure_isolated(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    seed(s, 2)

    d = build_digest(
        s,
        "m1",
        Directory(roster_file(tmp_path)),
    )
    plans = plan_emails(
        d,
        Directory(roster_file(tmp_path)),
    )

    sent = []

    class Fake:
        def __init__(self, *a, **k):
            pass

        def ehlo(self):
            pass

        def has_extn(self, x):
            return False

        def login(self, *a):
            pass

        def quit(self):
            pass

        def send_message(self, m):
            if m["To"] == "sam@x.test":
                raise smtplib.SMTPRecipientsRefused({})
            sent.append(m["To"])

    kw = {
        "sender": "a@b.test",
        "send": True,
        "host": "h",
        "smtp_factory": Fake,
        "sleep": lambda s: None,
    }

    r1 = deliver(plans, s, "m1", **kw)

    assert sent == ["priya@x.test"]
    assert {x["status"] for x in r1} >= {"sent", "failed"}

    r2 = deliver(plans, s, "m1", **kw)

    assert [x["status"] for x in r2 if x["to"] == "priya@x.test"] == ["unchanged"]  # not re-sent


def test_ics_stable_uid_allday_and_timezone():
    a = PushItem(
        id="act_1",
        kind="action",
        title="Send draft",
        owner="Priya",
        deadline=date(2025, 3, 14),
    )

    b = PushItem(
        id="act_2",
        kind="action",
        title="Ship",
        deadline=date(2025, 3, 13),
        deadline_time=time(17, 0),
    )

    events = Calendar.from_ical(build_ics([a, b], NOW)).walk("VEVENT")

    ev = {str(e["uid"]): e for e in events}

    assert set(ev) == {
        "act_1@meeting-copilot",
        "act_2@meeting-copilot",
    }

    assert ev["act_1@meeting-copilot"]["dtend"].dt == date(2025, 3, 15)

    start = ev["act_2@meeting-copilot"]["dtstart"].dt

    assert start.hour == 11
    assert start.minute == 30  # 17:00 IST

    empty_item = PushItem(
        id="x",
        kind="action",
        title="t",
    )

    assert build_ics([empty_item], NOW).count(b"BEGIN:VEVENT") == 0


def test_slack_escapes_mentions(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    seed(s)

    s.update_item(
        "act_1",
        edits={"title": "<!channel> wire <https://evil|money>"},
    )

    txt = json.dumps(
        build_payload(
            build_digest(
                s,
                "m1",
                Directory(roster_file(tmp_path)),
            )
        )
    )

    assert "<!channel>" not in txt
    assert esc("<!channel>") == "&lt;!channel&gt;"
