from dataclasses import dataclass, field

from copilot.config import settings
from copilot.integrations.base import PushItem
from copilot.integrations.directory import Directory
from copilot.integrations.payload import build_push_items
from copilot.store import Store


@dataclass
class MeetingDigest:
    meeting_id: str
    title: str
    date: str
    url: str
    roster: list[str]
    decisions: list[PushItem] = field(default_factory=list)
    actions: list[PushItem] = field(default_factory=list)  # committed, approved
    unowned: list[PushItem] = field(default_factory=list)
    questions: list[PushItem] = field(default_factory=list)  # unresolved only
    followups: list[PushItem] = field(default_factory=list)

    def by_owner(self) -> dict[str, list[PushItem]]:
        out: dict[str, list[PushItem]] = {}
        for a in self.actions:
            if a.owner:
                out.setdefault(a.owner, []).append(a)
        return out


def build_digest(store: Store, mid: str, directory: Directory | None = None) -> MeetingDigest:
    m = store.meeting_obj(mid)
    items = build_push_items(
        store,
        mid,
        ("action", "decision", "question", "followup"),
        directory or Directory(),
        settings.public_url,
    )
    d = MeetingDigest(
        meeting_id=mid,
        title=m.title or mid,
        date=m.date.isoformat(),
        url=f"{settings.public_url.rstrip('/')}/?meeting={mid}",
        roster=m.roster,
    )
    for i in items:
        if i.kind == "decision":
            d.decisions.append(i)
        elif i.kind == "question" and not i.answered:
            d.questions.append(i)
        elif i.kind == "followup":
            d.followups.append(i)
        elif i.kind == "action" and i.status == "committed":
            (d.actions if i.owner else d.unowned).append(i)
    return d


def to_markdown(d: MeetingDigest) -> str:
    def due(a: PushItem) -> str:
        if not a.deadline:
            return ""
        t = f" {a.deadline_time:%H:%M}" if a.deadline_time else ""
        return (
            f" (due {a.deadline}{t}{', confirm date' if 'ambiguous_deadline' in a.flags else ''})"
        )

    L = [f"# {d.title} ({d.date})", ""]
    if d.decisions:
        L += ["## Decisions"] + [f"- {x.title}" for x in d.decisions] + [""]
    for owner, acts in sorted(d.by_owner().items()):
        L += [f"## {owner}"] + [f"- {a.title}{due(a)}" for a in acts] + [""]
    if d.unowned:
        L += ["## Needs an owner"] + [f"- {a.title}{due(a)}" for a in d.unowned] + [""]
    if d.questions:
        L += ["## Open questions"] + [f"- {q.title}" for q in d.questions] + [""]
    if d.followups:
        L += ["## Follow-ups"] + [f"- {f.title}" for f in d.followups] + [""]
    return "\n".join(L)
