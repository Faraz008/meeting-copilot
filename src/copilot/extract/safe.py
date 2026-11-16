import logging
from dataclasses import dataclass, field

from copilot.extract.pipeline import PipelineConfig, run_pipeline
from copilot.models import ExtractionResult, Meeting
from copilot.parsers.transcript import build_roster, parse_transcript
from copilot.validate.inputs import InputError, prepare_turns

log = logging.getLogger(__name__)


@dataclass
class SafeResult:
    status: str  # ok | partial | rejected | failed
    result: ExtractionResult | None = None
    report: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error_code: str | None = None
    error: str | None = None


def sanity_warnings(result: ExtractionResult, n_turns: int) -> list[str]:
    w = []
    acts = [a for a in result.action_items if a.status != "superseded"]

    if n_turns and len(acts) / n_turns * 100 > 15:
        w.append(
            f"{len(acts)} action items in {n_turns} turns "
            "is unusually many: review for over-extraction."
        )

    committed = [a for a in acts if a.status == "committed"]

    if len(committed) >= 4 and sum(a.owner is None for a in committed) / len(committed) > 0.5:
        w.append("Most committed items have no owner: check speaker labels.")

    if n_turns > 150 and not (acts or result.decisions or result.open_questions):
        w.append("Nothing was extracted from a long meeting: check the input and provider status.")

    return w


def run_safe(
    raw: str,
    router,
    *,
    meeting_id: str,
    meeting_date,
    timezone: str = "Asia/Kolkata",
    roster: list[str] | None = None,
    aliases: dict | None = None,
    cfg: PipelineConfig | None = None,
) -> SafeResult:
    try:
        turns = parse_transcript(raw)
        turns, warns = prepare_turns(turns)

    except InputError as e:
        return SafeResult(
            "rejected",
            error_code=e.code,
            error=str(e),
        )

    except ValueError as e:
        return SafeResult(
            "rejected",
            error_code="unparseable",
            error=str(e),
        )

    meeting = Meeting(
        meeting_id=meeting_id,
        date=meeting_date,
        timezone=timezone,
        roster=roster or build_roster(turns),
        aliases=aliases or {},
        turns=turns,
    )

    try:
        out = run_pipeline(meeting, router, cfg)

    except Exception as e:
        # service boundary: never leak a stack trace to a user
        log.exception("pipeline crashed for %s", meeting_id)

        return SafeResult(
            "failed",
            warnings=warns,
            error_code="internal",
            error=f"{type(e).__name__}",
        )

    rep = out.report

    if rep["chunks"] and len(rep["failed_chunks"]) == rep["chunks"]:
        return SafeResult(
            "failed",
            report=rep,
            warnings=warns,
            error_code="all_chunks_failed",
            error=(
                "Every extraction call failed (provider limits or outage). Nothing was extracted."
            ),
        )

    warns += sanity_warnings(out.result, len(turns))

    return SafeResult(
        "ok" if rep["complete"] else "partial",
        out.result,
        rep,
        warns,
    )
