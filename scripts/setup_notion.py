import httpx

from copilot.config import settings
from copilot.integrations.notion import NOTION_VERSION, TYPE_LABEL


def sel(*names):
    return {"select": {"options": [{"name": n} for n in names]}}


props = {
    "Name": {"title": {}},
    "Type": sel(*TYPE_LABEL.values()),
    "Stage": sel("To do", "In progress", "Done"),
    "Owner": {"rich_text": {}},
    "Deadline": {"date": {}},
    "Priority": sel("high", "normal", "low"),
    "Meeting": {"rich_text": {}},
    "Meeting link": {"url": {}},
    "Flags": {"multi_select": {"options": []}},
    "Evidence": {"rich_text": {}},
    "Copilot ID": {"rich_text": {}},
}

r = httpx.post(
    "https://api.notion.com/v1/databases",
    timeout=30,
    headers={
        "Authorization": f"Bearer {settings.notion_token}",
        "Notion-Version": NOTION_VERSION,
    },
    json={
        "parent": {
            "type": "page_id",
            "page_id": settings.notion_parent_page_id,
        },
        "title": [{"type": "text", "text": {"content": "Meeting Co-Pilot"}}],
        "properties": props,
    },
)

r.raise_for_status()

print("Put this in .env -> NOTION_DATABASE_ID=" + r.json()["id"])
