from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

from copilot.integrations.base import PushItem


def build_ics(
    items: list[PushItem],
    now: datetime | None = None,
) -> bytes:
    """Stable UID per item: re-importing an updated file updates the event."""
    now = now or datetime.now(UTC)

    cal = Calendar()
    cal.add("prodid", "-//Meeting Co-Pilot//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")

    for it in items:
        if not it.deadline:
            continue

        ev = Event()
        ev.add("uid", f"{it.id}@meeting-copilot")
        ev.add("summary", f"Due: {it.title}"[:200])

        if it.deadline_time:
            start = datetime.combine(
                it.deadline,
                it.deadline_time,
                tzinfo=ZoneInfo(it.timezone),
            ).astimezone(UTC)

            ev.add("dtstart", start)
            ev.add("dtend", start + timedelta(minutes=30))
        else:
            ev.add("dtstart", it.deadline)
            ev.add("dtend", it.deadline + timedelta(days=1))

        note = (
            ["Deadline is ambiguous: please confirm."] if "ambiguous_deadline" in it.flags else []
        )

        description = [
            f"Owner: {it.owner or 'unassigned'}",
            f"From: {it.meeting_title or it.meeting_id} ({it.meeting_date})",
            *note,
        ]

        ev.add("description", "\n".join(description))
        ev.add("dtstamp", now)
        ev.add("last-modified", now)
        ev.add("sequence", int(now.timestamp() // 60))

        cal.add_component(ev)

    return cal.to_ical()
