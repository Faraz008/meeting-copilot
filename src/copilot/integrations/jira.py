import json
import re
import time

import httpx

from copilot.integrations.base import PushItem
from copilot.integrations.http import ApiClient, BadRequest

PRIORITY = {
    "high": "High",
    "normal": "Medium",
    "low": "Low",
}

OPTIONAL = {"priority", "duedate", "assignee"}


def _text(s: str, link: str | None = None) -> dict:
    node = {"type": "text", "text": s}

    if link:
        node["marks"] = [
            {
                "type": "link",
                "attrs": {"href": link},
            }
        ]

    return node


def _p(*nodes: dict) -> dict:
    return {
        "type": "paragraph",
        "content": [node for node in nodes if node.get("text")],
    }


def adf(it: PushItem) -> dict:
    head = [_text(f"From meeting: {it.meeting_title or it.meeting_id} ({it.meeting_date})")]

    if it.meeting_url:
        head += [
            _text(" · "),
            _text("open in Co-Pilot", it.meeting_url),
        ]

    body = [_p(*head)]

    if it.owner:
        body.append(_p(_text(f"Owner in transcript: {it.owner}")))

    if it.condition:
        body.append(_p(_text(f"Condition: {it.condition}")))

    if it.flags:
        body.append(_p(_text("Needs review: " + ", ".join(it.flags))))

    if it.evidence:
        body.append(_p(_text("Evidence:")))

        body += [
            {
                "type": "blockquote",
                "content": [_p(_text(f'{speaker}: "{quote}"'))],
            }
            for _, speaker, quote in it.evidence[:3]
        ]

    return {
        "type": "doc",
        "version": 1,
        "content": body,
    }


def _field_errors(body: str) -> dict:
    try:
        return json.loads(body).get("errors", {}) or {}
    except (ValueError, AttributeError):
        return {}


class JiraTarget:
    name = "jira"

    def __init__(
        self,
        base_url: str,
        email: str,
        token: str,
        project: str,
        *,
        issue_type: str = "Task",
        set_priority: bool = False,
        client: httpx.Client | None = None,
        rpm: float = 120,
        sleep=time.sleep,
    ):
        self.base = base_url.rstrip("/")
        self.project = project
        self.issue_type = issue_type
        self.set_priority = set_priority

        self.api = ApiClient(
            self.base,
            auth=(email, token),
            rpm=rpm,
            client=client,
            sleep=sleep,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    def _fields(
        self,
        it: PushItem,
        *,
        create: bool,
    ) -> dict:
        fields: dict = {
            "summary": it.title[:250] or "(untitled)",
            "description": adf(it),
        }

        if create:
            fields |= {
                "project": {"key": self.project},
                "issuetype": {"name": self.issue_type},
                "labels": [
                    "meeting-copilot",
                    f"copilot-{it.id}",
                ],
            }

            if it.deadline:
                fields["duedate"] = it.deadline.isoformat()

            if it.jira_account_id:
                # Create-time only: humans own it afterwards.
                fields["assignee"] = {"accountId": it.jira_account_id}
        else:
            fields["duedate"] = it.deadline.isoformat() if it.deadline else None

        if self.set_priority:
            fields["priority"] = {"name": PRIORITY[it.priority]}

        return fields

    def _with_fallback(
        self,
        method: str,
        path: str,
        fields: dict,
    ):
        for attempt in (1, 2):
            try:
                return self.api.request(
                    method,
                    path,
                    json={"fields": fields},
                )
            except BadRequest as e:
                bad = set(_field_errors(e.body)) & OPTIONAL

                if not bad or attempt == 2:
                    raise

                for key in bad:
                    fields.pop(key, None)

    def find(self, item_id: str):
        if not re.fullmatch(r"[\w-]+", item_id):
            return None

        r = self.api.request(
            "GET",
            "/rest/api/3/search/jql",
            params={
                "jql": (f'project = "{self.project}" AND labels = "copilot-{item_id}"'),
                "fields": "summary",
                "maxResults": 1,
            },
        )

        issues = r.json().get("issues", [])

        if not issues:
            return None

        key = issues[0]["key"]
        return key, f"{self.base}/browse/{key}"

    def create(self, it: PushItem):
        response = self._with_fallback(
            "POST",
            "/rest/api/3/issue",
            self._fields(it, create=True),
        )

        key = response.json()["key"]

        return key, f"{self.base}/browse/{key}"

    def update(self, external_id: str, it: PushItem):
        self._with_fallback(
            "PUT",
            f"/rest/api/3/issue/{external_id}",
            self._fields(it, create=False),
        )

        return f"{self.base}/browse/{external_id}"

    def check(self) -> str:
        r = self.api.request(
            "GET",
            "/rest/api/3/myself",
        )

        return f"ok as {r.json().get('displayName', '?')}"
