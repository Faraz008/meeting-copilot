import time

import httpx

from copilot.integrations.base import PushItem
from copilot.integrations.http import ApiClient, BadRequest, NotFound

NOTION_VERSION = "2022-06-28"

TYPE_LABEL = {
    "action": "Action",
    "decision": "Decision",
    "question": "Open question",
    "followup": "Follow-up",
}


def _rt(s: str | None, n: int = 1900) -> list[dict]:
    return [{"type": "text", "text": {"content": s[:n]}}] if s else []


class NotionTarget:
    name = "notion"

    def __init__(
        self,
        token: str,
        database_id: str,
        *,
        client: httpx.Client | None = None,
        rpm: float = 150,
        sleep=time.sleep,
    ):
        self.db = database_id
        self.api = ApiClient(
            "https://api.notion.com/v1",
            rpm=rpm,
            client=client,
            sleep=sleep,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
        )

    def _props(self, it: PushItem, *, create: bool) -> dict:
        if it.deadline:
            start = it.deadline.isoformat()
            date_val: dict | None = {"start": start}

            if it.deadline_time:
                date_val = {
                    "start": (f"{start}T{it.deadline_time.strftime('%H:%M:%S')}"),
                    "time_zone": it.timezone,
                }
        else:
            date_val = None

        ev = " | ".join(f'{sp}: "{q}"' for _, sp, q in it.evidence[:3])

        props = {
            "Name": {"title": _rt(it.title) or _rt("(untitled)")},
            "Type": {"select": {"name": TYPE_LABEL[it.kind]}},
            "Owner": {"rich_text": _rt(it.owner)},
            "Deadline": {"date": date_val},
            "Priority": {"select": {"name": it.priority}},
            "Meeting": {
                "rich_text": _rt(f"{it.meeting_title or it.meeting_id} ({it.meeting_date})")
            },
            "Meeting link": {"url": it.meeting_url},
            "Flags": {"multi_select": [{"name": flag} for flag in it.flags]},
            "Evidence": {"rich_text": _rt(ev)},
            "Copilot ID": {"rich_text": _rt(it.id)},
        }

        if create:
            # Humans own Stage afterwards.
            props["Stage"] = {"select": {"name": "To do"}}

        return props

    def find(self, item_id: str):
        r = self.api.request(
            "POST",
            f"/databases/{self.db}/query",
            json={
                "filter": {
                    "property": "Copilot ID",
                    "rich_text": {"equals": item_id},
                },
                "page_size": 1,
            },
        )

        res = r.json().get("results", [])

        return (res[0]["id"], res[0].get("url", "")) if res else None

    def create(self, it: PushItem):
        r = self.api.request(
            "POST",
            "/pages",
            json={
                "parent": {"database_id": self.db},
                "properties": self._props(it, create=True),
            },
        )

        d = r.json()
        return d["id"], d.get("url", "")

    def update(self, external_id: str, it: PushItem):
        try:
            r = self.api.request(
                "PATCH",
                f"/pages/{external_id}",
                json={
                    "properties": self._props(
                        it,
                        create=False,
                    )
                },
            )
        except BadRequest as e:
            if "archived" in e.body.lower():
                raise NotFound("page archived") from e
            raise

        return r.json().get("url")

    def check(self) -> str:
        r = self.api.request("GET", "/users/me")

        # A 404 here means the database is not shared
        # with the integration.
        self.api.request(
            "GET",
            f"/databases/{self.db}",
        )

        return f"ok as {r.json().get('name', 'integration')}"
