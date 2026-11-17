import hashlib
from dataclasses import dataclass, field
from datetime import date

from copilot.config import settings
from copilot.extract.pipeline import PipelineConfig
from copilot.extract.safe import run_safe
from copilot.integrations.base import Outcome
from copilot.integrations.directory import Directory
from copilot.integrations.engine import push_items
from copilot.integrations.payload import build_push_items
from copilot.llm.factory import build_router
from copilot.llm.redact import redact as scrub
from copilot.store import Store


class ConfigError(ValueError): ...


@dataclass
class PushReport:
    outcomes: list[Outcome]
    orphans: list[dict]

    def summary(self) -> dict:
        from collections import Counter

        return dict(Counter(o.status for o in self.outcomes))


def make_target(name: str, *, client=None):
    s = settings

    if name == "notion":
        if not (s.notion_token and s.notion_database_id):
            raise ConfigError("Set NOTION_TOKEN and NOTION_DATABASE_ID (see docs/integrations.md).")

        from copilot.integrations.notion import NotionTarget

        return NotionTarget(
            s.notion_token,
            s.notion_database_id,
            client=client,
        )

    if name == "jira":
        if not all(
            [
                s.jira_base_url,
                s.jira_email,
                s.jira_api_token,
                s.jira_project_key,
            ]
        ):
            raise ConfigError("Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN and JIRA_PROJECT_KEY.")

        from copilot.integrations.jira import JiraTarget

        return JiraTarget(
            s.jira_base_url,
            s.jira_email,
            s.jira_api_token,
            s.jira_project_key,
            issue_type=s.jira_issue_type,
            set_priority=s.jira_set_priority,
            client=client,
        )

    raise ConfigError(f"Unknown target {name!r}")


def push(
    store: Store,
    mid: str,
    target_name: str,
    *,
    dry_run: bool = True,
    force: bool = False,
    kinds: tuple[str, ...] | None = None,
    target=None,
) -> PushReport:
    if settings.demo_mode:
        raise ConfigError("Demo mode: pushing is disabled.")

    target = target or make_target(target_name)

    kinds = kinds or (
        ("action",) if target_name == "jira" else ("action", "decision", "question", "followup")
    )

    items = build_push_items(
        store,
        mid,
        kinds,
        Directory(),
        settings.public_url,
    )

    outcomes = push_items(
        store,
        target,
        items,
        dry_run=dry_run,
        force=force,
    )

    current = {item.id for item in items}

    orphans = [
        item
        for item in store.list_pushes(mid)
        if item["target"] == target.name
        and item["status"] == "ok"
        and item["item_id"] not in current
        and not item["item_id"].startswith("meeting:")
    ]

    return PushReport(outcomes, orphans)


@dataclass
class IngestOutcome:
    meeting_id: str
    status: str
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


def new_meeting_id(raw: str, meeting_date: date) -> str:
    """Generate a stable ID from transcript content and meeting date.

    Re-ingesting the same transcript on the same date preserves
    its review state.
    """
    content = f"{meeting_date}|{raw}".encode()
    digest = hashlib.sha1(content).hexdigest()[:10]

    return f"m_{digest}"


def ingest(
    raw: str,
    *,
    meeting_date: date,
    title: str | None = None,
    timezone: str = "Asia/Kolkata",
    roster: list[str] | None = None,
    aliases: dict | None = None,
    speaker_map: dict[str, str] | None = None,
    provider: str | None = None,
    local_only: bool = False,
    redact: bool = False,
    store: Store | None = None,
    router=None,
    cfg: PipelineConfig | None = None,
    on_progress=None,
    meeting_id: str | None = None,
) -> IngestOutcome:
    """Ingest a transcript and persist its extraction results."""
    store = store or Store()

    mid = meeting_id or new_meeting_id(raw, meeting_date)

    store.begin_meeting(
        mid,
        title,
        meeting_date,
        timezone,
    )

    try:
        router = router or build_router(
            order=[provider] if provider else None,
            local_only=local_only,
            run_id=mid,
        )

        redactor = None

        if redact:
            from copilot.privacy.pii import Redactor

            redactor = Redactor()

        res = run_safe(
            raw,
            router,
            meeting_id=mid,
            meeting_date=meeting_date,
            timezone=timezone,
            roster=roster,
            aliases=aliases or Directory().aliases(),
            cfg=cfg,
            speaker_map=speaker_map,
            redactor=redactor,
            on_progress=on_progress,
            title=title,
        )

    except Exception as exc:
        # Handle configuration errors and other ingestion failures.
        err = scrub(f"{type(exc).__name__}: {exc}")[:300]

        store.finish_meeting(
            mid,
            "failed",
            error=err,
        )

        return IngestOutcome(
            mid,
            "failed",
            err,
        )

    if res.status in ("rejected", "failed"):
        store.finish_meeting(
            mid,
            res.status,
            report=res.report,
            warnings=res.warnings,
            error=res.error,
        )

        return IngestOutcome(
            mid,
            res.status,
            res.error,
            res.warnings,
        )

    # Save extracted items before updating meeting status.
    store.save_extraction(
        mid,
        res.result,
    )

    store.finish_meeting(
        mid,
        res.status,
        meeting=res.meeting,
        report=res.report,
        warnings=res.warnings,
    )

    return IngestOutcome(
        mid,
        res.status,
        None,
        res.warnings,
    )


def approve_clean(
    store: Store,
    mid: str,
    min_conf: float = 0.8,
) -> int:
    """Automatically approve items that need no human decision.

    Actions must be committed, have an owner, contain no unresolved
    flags except a missing deadline, and meet the confidence threshold.

    Decisions must be active and meet the confidence threshold.
    """
    approved_count = 0

    for item in store.items(mid, include_stale=False):
        if item["state"] != "pending":
            continue

        flags = set(item["flags"])

        if flags - {"no_deadline"}:
            continue

        confidence = item["confidence"]

        is_action = (
            item["kind"] == "action"
            and item["status"] == "committed"
            and bool(item.get("owner"))
            and confidence >= min_conf
        )

        is_decision = (
            item["kind"] == "decision" and item.get("status") == "active" and confidence >= min_conf
        )

        if is_action or is_decision:
            store.update_item(
                item["id"],
                state="approved",
            )

            approved_count += 1

    return approved_count


def configured_providers() -> list[str]:
    """Return the configured LLM providers."""
    from copilot.config import settings as s

    available = {
        "groq": bool(s.groq_api_key and s.groq_model),
        "gemini": bool(s.gemini_api_key and s.gemini_model),
        "openrouter": bool(s.openrouter_api_key and s.openrouter_model),
        "ollama": bool(s.ollama_model),
    }

    return [provider for provider, configured in available.items() if configured]


def digest(store: Store, mid: str):
    from copilot.digest import build_digest

    return build_digest(store, mid)


def email(
    store: Store,
    mid: str,
    *,
    send: bool = False,
    force: bool = False,
    smtp_factory=None,
) -> list[dict]:
    from copilot.integrations.emailer import deliver, plan_emails

    if settings.demo_mode:
        raise ConfigError("Demo mode: email is disabled.")

    if send and not (settings.smtp_host and settings.smtp_from):
        raise ConfigError(
            "Set SMTP_HOST and SMTP_FROM (and SMTP_USER/SMTP_PASSWORD if your server needs them)."
        )

    plans = plan_emails(digest(store, mid), Directory())

    return deliver(
        plans,
        store,
        mid,
        sender=settings.smtp_from or "copilot@localhost",
        send=send,
        force=force,
        host=settings.smtp_host,
        port=settings.smtp_port,
        user=settings.smtp_user,
        password=settings.smtp_password,
        smtp_factory=smtp_factory,
    )


def ics_bytes(store: Store, mid: str) -> bytes:
    from copilot.integrations.ics import build_ics

    return build_ics([a for a in digest(store, mid).actions if a.deadline])


def slack(store: Store, mid: str, *, client=None) -> None:
    from copilot.integrations.slack import build_payload, post

    if settings.demo_mode or not settings.slack_webhook_url:
        raise ConfigError("Set SLACK_WEBHOOK_URL (disabled in demo mode).")
    post(settings.slack_webhook_url, build_payload(digest(store, mid)), client=client)
