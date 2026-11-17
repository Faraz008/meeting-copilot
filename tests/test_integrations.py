from dataclasses import replace
from types import SimpleNamespace

import httpx

from copilot import service
from copilot.integrations.base import PushItem
from copilot.integrations.directory import Directory
from copilot.integrations.engine import push_items
from copilot.integrations.jira import JiraTarget, adf
from copilot.integrations.notion import NotionTarget
from copilot.integrations.payload import build_push_items
from copilot.store import Store
from tests.helpers import seed


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def setup(tmp_path, n=1):
    store = Store(tmp_path / "t.sqlite")
    seed(store, n)

    def get_items():
        return build_push_items(
            store,
            "m1",
            ("action",),
            Directory(str(tmp_path / "none.json")),
            "http://ui",
        )

    return store, get_items


def notion(handler):
    return NotionTarget(
        "tok",
        "db1",
        client=client(handler),
        rpm=60000,
        sleep=lambda s: None,
    )


def ok_handler(calls, found=None):
    def handler(req):
        calls.append((req.method, req.url.path))

        if req.url.path.endswith("/query"):
            results = [found] if found else []
            return httpx.Response(200, json={"results": results})

        return httpx.Response(
            200,
            json={
                "id": "pg1",
                "url": "https://notion.so/pg1",
            },
        )

    return handler


def test_create_then_unchanged_then_update_on_edit(tmp_path):
    store, items = setup(tmp_path)
    calls = []
    target = notion(ok_handler(calls))

    assert push_items(store, target, items())[0].status == "created"

    call_count = len(calls)

    # Unchanged items should not trigger an HTTP request.
    outcome = push_items(store, target, items())[0]
    assert outcome.status == "unchanged"
    assert len(calls) == call_count

    store.update_item("act_1", edits={"owner": "Sam"})

    outcome = push_items(store, target, items())[0]
    assert outcome.status == "updated"
    assert calls[-1][0] == "PATCH"


def test_update_never_sends_stage(tmp_path):
    store, items = setup(tmp_path)
    bodies = []

    def handler(req):
        bodies.append((req.method, req.content.decode()))
        return httpx.Response(
            200,
            json={"id": "pg1", "results": []},
        )

    target = notion(handler)
    push_items(store, target, items())

    store.update_item("act_1", edits={"title": "Changed"})
    push_items(store, target, items())

    assert '"Stage"' in bodies[1][1]
    assert '"Stage"' not in bodies[-1][1]


def test_remote_deleted_or_archived_is_recreated(tmp_path):
    store, items = setup(tmp_path)
    mode = {"patch": 404}

    def handler(req):
        if req.method == "PATCH":
            return httpx.Response(
                mode["patch"],
                json={"message": "Can't edit block that is archived"},
            )

        return httpx.Response(
            200,
            json={
                "id": "pg2",
                "url": "u",
                "results": [],
            },
        )

    target = notion(handler)

    store.record_push(
        "act_1",
        "notion",
        "old",
        "u",
        "stale-hash",
        "ok",
    )

    assert push_items(store, target, items())[0].status == "created"

    mode["patch"] = 400

    store.record_push(
        "act_1",
        "notion",
        "old",
        "u",
        "stale-hash",
        "ok",
    )

    assert push_items(store, target, items())[0].status == "created"


def test_partial_failure_does_not_stop_the_batch(tmp_path):
    store, items = setup(tmp_path, 2)
    count = {"c": 0}

    def handler(req):
        if req.url.path.endswith("/query"):
            return httpx.Response(200, json={"results": []})

        count["c"] += 1

        if count["c"] == 1:
            return httpx.Response(400, json={"message": "bad"})

        return httpx.Response(
            200,
            json={"id": "pg", "url": "u"},
        )

    outcomes = push_items(store, notion(handler), items())

    assert [o.status for o in outcomes] == ["failed", "created"]
    assert store.get_push("act_1", "notion")["status"] == "failed"

    # Failed items should be retried.
    retry_target = notion(ok_handler([]))
    outcome = push_items(store, retry_target, items())[0]
    assert outcome.status == "created"


def test_find_before_create_adopts_existing_page(tmp_path):
    store, items = setup(tmp_path)
    calls = []

    target = notion(
        ok_handler(
            calls,
            found={"id": "pg9", "url": "u9"},
        )
    )

    assert push_items(store, target, items())[0].status == "updated"

    # Do not create a duplicate page.
    assert ("POST", "/v1/pages") not in calls


def test_auth_failure_aborts_remaining(tmp_path):
    store, items = setup(tmp_path, 2)

    outcomes = push_items(
        store,
        notion(lambda req: httpx.Response(401)),
        items(),
    )

    assert [o.status for o in outcomes] == ["failed", "skipped"]


def test_dry_run_makes_no_calls(tmp_path):
    store, items = setup(tmp_path)
    calls = []

    outcomes = push_items(
        store,
        notion(ok_handler(calls)),
        items(),
        dry_run=True,
    )

    assert outcomes[0].status == "would_create"
    assert calls == []


def test_rate_limit_is_retried(tmp_path):
    store, items = setup(tmp_path)
    count = {"c": 0}

    def handler(req):
        if req.url.path.endswith("/query"):
            return httpx.Response(200, json={"results": []})

        count["c"] += 1

        if count["c"] == 1:
            return httpx.Response(
                429,
                headers={"retry-after": "1"},
            )

        return httpx.Response(
            200,
            json={"id": "pg", "url": "u"},
        )

    outcome = push_items(store, notion(handler), items())[0]
    assert outcome.status == "created"


def test_jira_create_has_idempotency_label_and_drops_unsettable_fields(
    tmp_path,
):
    store, items = setup(tmp_path)
    sent = []

    def handler(req):
        if req.url.path.endswith("/search/jql"):
            return httpx.Response(200, json={"issues": []})

        body = req.content.decode()
        sent.append(body)

        if len(sent) == 1:
            return httpx.Response(
                400,
                json={"errors": {"duedate": "Field 'duedate' cannot be set."}},
            )

        return httpx.Response(201, json={"key": "PRJ-7"})

    target = JiraTarget(
        "https://x.atlassian.net",
        "a@b.c",
        "tok",
        "PRJ",
        client=client(handler),
        rpm=60000,
        sleep=lambda s: None,
    )

    outcome = push_items(store, target, items())[0]

    assert outcome.status == "created"
    assert outcome.external_id == "PRJ-7"
    assert outcome.url.endswith("/browse/PRJ-7")

    assert "copilot-act_1" in sent[0]
    assert "duedate" in sent[0]
    assert "duedate" not in sent[1]


def _no_empty_text(node):
    if isinstance(node, dict):
        assert not (node.get("type") == "text" and not node.get("text"))

        for value in node.values():
            _no_empty_text(value)

    elif isinstance(node, list):
        for value in node:
            _no_empty_text(value)


def test_adf_has_no_empty_text_nodes_and_keeps_hostile_text_as_text(
    tmp_path,
):
    item = PushItem(
        id="act_1",
        kind="action",
        title="",
        evidence=((0, "", "<script>x</script>"),),
        meeting_url=None,
    )

    document = adf(item)
    _no_empty_text(document)

    # Hostile text must remain data inside text nodes.
    assert "<script>" in str(document)


def test_fingerprint_ignores_owner_email():
    item = PushItem(
        id="act_1",
        kind="action",
        title="Send report",
        owner="Sam",
        owner_email="sam@example.com",
    )

    changed_email = replace(
        item,
        owner_email="another@example.com",
    )

    assert item.fingerprint() == changed_email.fingerprint()


def test_rejected_pushed_item_remains_in_pushes_and_becomes_orphan(
    tmp_path,
    monkeypatch,
):
    store, items = setup(tmp_path)
    target = notion(ok_handler([]))

    # First, successfully push the item.
    outcome = push_items(store, target, items())[0]
    assert outcome.status == "created"

    # Reject the item after it has been pushed.
    assert store.update_item("act_1", state="rejected")

    # Its historical push record must remain available.
    pushes = store.list_pushes("m1")

    assert len(pushes) == 1
    assert pushes[0]["item_id"] == "act_1"
    assert pushes[0]["target"] == "notion"
    assert pushes[0]["status"] == "ok"

    # Configure the service for this test.
    monkeypatch.setattr(
        service,
        "settings",
        SimpleNamespace(
            demo_mode=False,
            public_url="http://ui",
        ),
    )
    monkeypatch.setattr(
        service,
        "Directory",
        lambda: Directory(str(tmp_path / "none.json")),
    )

    # The rejected item is no longer eligible for pushing.
    report = service.push(
        store,
        "m1",
        "notion",
        target=target,
    )

    assert report.outcomes == []
    assert len(report.orphans) == 1
    assert report.orphans[0]["item_id"] == "act_1"
    assert report.orphans[0]["target"] == "notion"
