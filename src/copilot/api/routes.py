import secrets
import time
from datetime import date
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
from pydantic import BaseModel

from copilot import service
from copilot.config import settings
from copilot.store import Store

MAX_BYTES = 2_000_000


def require_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    if settings.api_key and not (x_api_key and secrets.compare_digest(x_api_key, settings.api_key)):
        raise HTTPException(401, "invalid or missing X-API-Key")


def get_store() -> Store:
    return Store()


router = APIRouter(dependencies=[Depends(require_key)])


class ExtractIn(BaseModel):
    text: str
    meeting_date: date
    title: str | None = None
    timezone: str = "Asia/Kolkata"
    roster: list[str] | None = None
    speaker_map: dict[str, str] | None = None
    provider: str | None = None
    local_only: bool = False
    redact: bool = False


class ItemPatch(BaseModel):
    state: Literal["pending", "approved", "rejected"] | None = None
    edits: dict | None = None


class PushIn(BaseModel):
    target: Literal["notion", "jira"]
    dry_run: bool = True
    force: bool = False


def _start(
    bg: BackgroundTasks,
    store: Store,
    raw: str,
    **kw,
) -> dict:
    try:
        ZoneInfo(kw["timezone"])
    except Exception:
        raise HTTPException(422, "unknown timezone") from None

    if len(raw.encode()) > MAX_BYTES:
        raise HTTPException(413, "transcript too large")

    mid = service.new_meeting_id(raw, kw["meeting_date"])
    row = store.get_meeting(mid)

    if row and row["status"] == "processing" and time.time() - (row["updated"] or 0) < 1800:
        raise HTTPException(
            409,
            "this meeting is already being processed",
        )

    store.begin_meeting(
        mid,
        kw.get("title"),
        kw["meeting_date"],
        kw["timezone"],
    )

    bg.add_task(service.ingest, raw, meeting_id=mid, **kw)

    return {
        "meeting_id": mid,
        "status": "processing",
    }


@router.post("/extract", status_code=202)
def extract(
    body: ExtractIn,
    bg: BackgroundTasks,
    store: Annotated[Store, Depends(get_store)],
):
    data = body.model_dump(exclude={"text"})
    return _start(bg, store, body.text, **data)


@router.post("/extract/upload", status_code=202)
async def extract_upload(
    bg: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    meeting_date: Annotated[date, Form()],
    title: Annotated[str | None, Form()] = None,
    timezone: Annotated[str, Form()] = "Asia/Kolkata",
    provider: Annotated[str | None, Form()] = None,
    local_only: Annotated[bool, Form()] = False,
    redact: Annotated[bool, Form()] = False,
    store: Annotated[Store, Depends(get_store)] = None,
):
    data = await file.read(MAX_BYTES + 1)

    return _start(
        bg,
        store,
        data.decode("utf-8", errors="replace"),
        meeting_date=meeting_date,
        title=title,
        timezone=timezone,
        provider=provider,
        local_only=local_only,
        redact=redact,
    )


@router.get("/meetings")
def meetings(
    store: Annotated[Store, Depends(get_store)],
):
    return store.list_meetings()


def _meeting_or_404(store: Store, mid: str) -> dict:
    row = store.get_meeting(mid)

    if not row:
        raise HTTPException(404, "meeting not found")

    return row


@router.get("/meetings/{mid}")
def meeting(
    mid: str,
    store: Annotated[Store, Depends(get_store)],
):
    row = _meeting_or_404(store, mid)

    return {
        k: row[k]
        for k in (
            "id",
            "title",
            "date",
            "timezone",
            "status",
            "report",
            "warnings",
            "error",
        )
    }


@router.get("/meetings/{mid}/items")
def items(
    mid: str,
    kind: str | None = None,
    state: str | None = None,
    store: Annotated[Store, Depends(get_store)] = None,
):
    _meeting_or_404(store, mid)

    return [
        {k: v for k, v in item.items() if k != "orig"}
        for item in store.items(mid, kind)
        if state is None or item["state"] == state
    ]


@router.patch("/items/{item_id}")
def patch_item(
    item_id: str,
    body: ItemPatch,
    store: Annotated[Store, Depends(get_store)] = None,
):
    try:
        if not store.update_item(
            item_id,
            state=body.state,
            edits=body.edits,
        ):
            raise HTTPException(404, "item not found")

    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    return {"ok": True}


@router.post("/meetings/{mid}/approve-clean")
def approve_clean(
    mid: str,
    min_conf: float = 0.8,
    store: Annotated[Store, Depends(get_store)] = None,
):
    _meeting_or_404(store, mid)

    return {"approved": service.approve_clean(store, mid, min_conf)}


@router.post("/meetings/{mid}/push")
def push(
    mid: str,
    body: PushIn,
    store: Annotated[Store, Depends(get_store)] = None,
):
    _meeting_or_404(store, mid)

    try:
        rep = service.push(
            store,
            mid,
            body.target,
            dry_run=body.dry_run,
            force=body.force,
        )
    except service.ConfigError as exc:
        raise HTTPException(400, str(exc)) from exc

    return {
        "summary": rep.summary(),
        "outcomes": [outcome.__dict__ for outcome in rep.outcomes],
        "orphans": rep.orphans,
    }


@router.get("/meetings/{mid}/export.md")
def export_md(
    mid: str,
    store: Annotated[Store, Depends(get_store)],
):
    from copilot.digest import to_markdown

    _meeting_or_404(store, mid)

    return Response(
        to_markdown(service.digest(store, mid)),
        media_type="text/markdown",
    )


@router.get("/meetings/{mid}/deadlines.ics")
def export_ics(
    mid: str,
    store: Annotated[Store, Depends(get_store)],
):
    _meeting_or_404(store, mid)

    return Response(
        service.ics_bytes(store, mid),
        media_type="text/calendar",
    )


@router.delete("/meetings/{mid}", status_code=204)
def delete(
    mid: str,
    store: Annotated[Store, Depends(get_store)],
):
    _meeting_or_404(store, mid)
    store.delete_meeting(mid)
