from datetime import date, time

from copilot.integrations.base import PushItem
from copilot.integrations.directory import Directory
from copilot.store import Store


def build_push_items(
    store: Store,
    mid: str,
    kinds: tuple[str, ...],
    directory: Directory,
    public_url: str,
) -> list[PushItem]:
    m = store.meeting_obj(mid)
    out = []

    for it in store.items(mid, include_stale=False):
        if it["kind"] not in kinds or it["state"] != "approved":
            continue

        if (it["kind"] == "action" and it["status"] == "superseded") or (
            it["kind"] == "decision" and it.get("status", "active") != "active"
        ):
            continue

        title = it.get("title") or it.get("summary") or it.get("question") or it.get("topic") or ""

        ev = tuple(
            (
                e["turn_idx"],
                (m.turns[e["turn_idx"]].speaker if e["turn_idx"] < len(m.turns) else None) or "?",
                e["quote"],
            )
            for e in it["evidence"]
        )

        owner = it.get("owner")

        out.append(
            PushItem(
                id=it["id"],
                kind=it["kind"],
                title=title,
                owner=owner,
                owner_email=directory.email(owner),
                jira_account_id=directory.jira_id(owner),
                deadline=(date.fromisoformat(it["deadline"]) if it.get("deadline") else None),
                deadline_time=(
                    time.fromisoformat(it["deadline_time"]) if it.get("deadline_time") else None
                ),
                timezone=m.timezone,
                priority=it.get("priority", "normal"),
                status=it.get("status", "committed"),
                condition=it.get("condition"),
                flags=tuple(it["flags"]),
                evidence=ev,
                answered=it.get("answered"),
                meeting_id=mid,
                meeting_title=m.title,
                meeting_date=m.date.isoformat(),
                meeting_url=(f"{public_url.rstrip('/')}/?meeting={mid}"),
            )
        )

    return out
