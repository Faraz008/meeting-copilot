import json

from fastapi.testclient import TestClient

from copilot.api.main import app
from copilot.api.routes import get_store
from copilot.config import settings
from copilot.store import Store
from tests.helpers import seed


def test_health():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def client(tmp_path, monkeypatch):
    s = Store(tmp_path / "api.sqlite")
    app.dependency_overrides[get_store] = lambda: s
    return TestClient(app), s


def test_auth_required_when_key_set(tmp_path, monkeypatch):
    c, s = client(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "api_key", "secret-key-123")

    assert c.get("/meetings").status_code == 401
    assert (
        c.get(
            "/meetings",
            headers={"X-API-Key": "secret-key-123"},
        ).status_code
        == 200
    )
    assert c.get("/health").status_code == 200


def test_review_flow_and_validation(tmp_path, monkeypatch):
    c, s = client(tmp_path, monkeypatch)
    seed(s, 2, approve=False)

    assert c.post("/meetings/m1/approve-clean").json() == {"approved": 1}
    assert (
        c.patch(
            "/items/act_2",
            json={"edits": {"owner": "Dan"}, "state": "approved"},
        ).status_code
        == 200
    )
    assert (
        c.patch(
            "/items/act_2",
            json={"edits": {"deadline": "soon"}},
        ).status_code
        == 422
    )
    assert (
        c.patch(
            "/items/nope",
            json={"state": "approved"},
        ).status_code
        == 404
    )

    assert [i["state"] for i in c.get("/meetings/m1/items").json()] == ["approved", "approved"]

    assert "## Priya" in c.get("/meetings/m1/export.md").text
    assert c.get("/meetings/m1/deadlines.ics").headers["content-type"].startswith("text/calendar")


def test_push_defaults_to_dry_run_and_reports_missing_config(tmp_path, monkeypatch):
    c, s = client(tmp_path, monkeypatch)
    seed(s)

    monkeypatch.setattr(settings, "notion_token", None)

    r = c.post("/meetings/m1/push", json={"target": "notion"})
    assert r.status_code == 400
    assert "NOTION_TOKEN" in r.json()["detail"]


def test_extract_runs_in_background_and_rejects_bad_input(tmp_path, monkeypatch):
    c, s = client(tmp_path, monkeypatch)

    from copilot import service
    from copilot.llm.router import Router
    from tests.fakes import ConstProvider

    empty = json.dumps(
        {
            "action_items": [],
            "decisions": [],
            "open_questions": [],
            "follow_ups": [],
        }
    )

    monkeypatch.setattr(
        service,
        "build_router",
        lambda **k: Router(
            [ConstProvider("c", empty)],
            sleep=lambda s: None,
        ),
    )

    raw = "\n".join(
        f"Ana: we should talk about item {i} in the release plan today okay" for i in range(12)
    )

    r = c.post(
        "/extract",
        json={"text": raw, "meeting_date": "2025-03-12"},
    )
    assert r.status_code == 202

    meeting = c.get(f"/meetings/{r.json()['meeting_id']}").json()
    assert meeting["status"] in {"ok", "partial", "processing"}

    assert (
        c.post(
            "/extract",
            json={
                "text": raw,
                "meeting_date": "2025-03-12",
                "timezone": "Mars/Base",
            },
        ).status_code
        == 422
    )

    big = c.post(
        "/extract",
        json={
            "text": "x " * 1_100_000,
            "meeting_date": "2025-03-12",
        },
    )
    assert big.status_code == 413
