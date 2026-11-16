import hashlib
from dataclasses import dataclass, field
from datetime import date

from copilot.extract.pipeline import PipelineConfig
from copilot.extract.safe import run_safe
from copilot.integrations.directory import Directory
from copilot.llm.factory import build_router
from copilot.llm.redact import redact as scrub
from copilot.store import Store


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
