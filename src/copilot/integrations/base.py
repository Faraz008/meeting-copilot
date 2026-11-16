import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, time
from typing import Protocol


@dataclass(frozen=True)
class PushItem:
    id: str
    kind: str  # action | decision | question | followup
    title: str
    owner: str | None = None
    owner_email: str | None = None
    jira_account_id: str | None = None
    deadline: date | None = None
    deadline_time: time | None = None
    timezone: str = "Asia/Kolkata"
    priority: str = "normal"
    status: str = "committed"
    condition: str | None = None
    flags: tuple[str, ...] = ()
    evidence: tuple[tuple[int, str, str], ...] = ()  # (turn_idx, speaker, quote)
    answered: bool | None = None
    meeting_id: str = ""
    meeting_title: str | None = None
    meeting_date: str = ""
    meeting_url: str | None = None

    def fingerprint(self) -> str:
        d = asdict(self)
        # Directory data, create-time only
        d.pop("owner_email")
        d.pop("jira_account_id")

        payload = json.dumps(
            d,
            sort_keys=True,
            default=str,
        ).encode()

        return hashlib.sha256(payload).hexdigest()


@dataclass
class Outcome:
    item_id: str
    target: str
    status: str  # created | updated | unchanged | failed | skipped | would_create | would_update
    external_id: str | None = None
    url: str | None = None
    error: str | None = None


class Target(Protocol):
    name: str

    def find(self, item_id: str) -> tuple[str, str] | None: ...
    def create(self, it: PushItem) -> tuple[str, str]: ...
    def update(self, external_id: str, it: PushItem) -> str | None: ...
    def check(self) -> str: ...
