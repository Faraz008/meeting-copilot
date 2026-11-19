from datetime import date

import pytest

from copilot import service
from copilot.config import settings
from copilot.integrations.notion import NotionTarget
from copilot.io import ROOT
from copilot.llm.base import PermanentError
from copilot.llm.router import Router
from copilot.store import Store
from tests.fakes import FakeProvider
from tests.helpers import seed
from tests.test_integrations import client, ok_handler
from tests.test_pipeline import EXTRACT, JUDGE_D, JUDGE_Q

RAW = (ROOT / "data/synthetic/s01_cli.txt").read_text(encoding="utf-8")

D = date(2025, 3, 12)


def run(store, responses):
    router = Router(
        [FakeProvider("fake", responses)],
        sleep=lambda s: None,
    )

    return service.ingest(
        RAW,
        meeting_date=D,
        roster=["Priya", "Sam", "Dan"],
        store=store,
        router=router,
    )


def test_ingest_stores_items_and_reingest_keeps_review_state(
    tmp_path,
):
    store = Store(tmp_path / "t.sqlite")

    out = run(
        store,
        [EXTRACT, JUDGE_Q, JUDGE_D],
    )

    assert out.status == "ok"

    titles = {item["title"] for item in store.items(out.meeting_id, "action")}

    assert "Invented task" not in titles
    assert "Send revised pricing copy" in titles

    assert service.approve_clean(store, out.meeting_id) >= 1

    # Same transcript again.
    run(
        store,
        [EXTRACT, JUDGE_Q, JUDGE_D],
    )

    assert any(item["state"] == "approved" for item in store.items(out.meeting_id, "action"))


def test_ingest_provider_outage_is_failed_not_exception(
    tmp_path,
):
    store = Store(tmp_path / "t.sqlite")

    router = Router(
        [
            FakeProvider(
                "fake",
                [PermanentError("bad key")] * 5,
            )
        ],
        sleep=lambda s: None,
    )

    out = service.ingest(
        RAW,
        meeting_date=D,
        store=store,
        router=router,
    )

    assert out.status == "failed"

    assert store.get_meeting(out.meeting_id)["status"] == "failed"


def test_rejected_after_push_is_reported_as_orphan(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "demo_mode", False)

    monkeypatch.setattr(
        settings,
        "roster_path",
        str(tmp_path / "none.json"),
    )

    store = Store(tmp_path / "t.sqlite")
    seed(store, 2)

    target = NotionTarget(
        "tok",
        "db",
        client=client(ok_handler([])),
        rpm=60000,
        sleep=lambda x: None,
    )

    first_report = service.push(
        store,
        "m1",
        "notion",
        dry_run=False,
        target=target,
    )

    assert first_report.summary() == {"created": 2}

    store.update_item("act_2", state="rejected")

    report = service.push(
        store,
        "m1",
        "notion",
        dry_run=False,
        target=target,
    )

    assert [orphan["item_id"] for orphan in report.orphans] == ["act_2"]


def test_demo_mode_blocks_every_outbound_action(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "demo_mode", True)

    store = Store(tmp_path / "t.sqlite")
    seed(store)

    actions = [
        lambda: service.push(store, "m1", "notion"),
        lambda: service.email(store, "m1", send=True),
        lambda: service.slack(store, "m1"),
    ]

    for action in actions:
        with pytest.raises(service.ConfigError):
            action()
