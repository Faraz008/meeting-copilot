import json
from pathlib import Path

from copilot.config import settings


class Directory:
    """config/roster.json (gitignored):
    {
        "Priya Sharma": {
            "email": "priya@example.com",
            "jira_account_id": "5b10...",
            "aliases": ["Pree-ya"]
        }
    }
    """

    def __init__(self, path: str | None = None):
        p = Path(path or settings.roster_path)
        self.data: dict[str, dict] = json.loads(p.read_text("utf-8")) if p.exists() else {}
        self._ci = {k.lower(): v for k, v in self.data.items()}

    def _get(self, name: str | None) -> dict:
        return self._ci.get((name or "").lower(), {})

    def email(self, name: str | None) -> str | None:
        return self._get(name).get("email")

    def jira_id(self, name: str | None) -> str | None:
        return self._get(name).get("jira_account_id")

    def aliases(self) -> dict[str, list[str]]:
        return {k: v.get("aliases", []) for k, v in self.data.items() if v.get("aliases")}
