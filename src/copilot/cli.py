import datetime as dt
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from copilot import service
from copilot.config import settings
from copilot.store import Store

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Meeting Co-Pilot",
)


def _store() -> Store:
    return Store()


def _fail(msg: str) -> None:
    typer.secho(
        msg,
        fg=typer.colors.RED,
        err=True,
    )
    raise typer.Exit(1)


@app.command()
def run(
    path: Path,
    meeting_date: str = typer.Option(
        ...,
        "--date",
        help="YYYY-MM-DD",
    ),
    title: str = typer.Option(None),
    provider: str = typer.Option(None),
    tz: str = typer.Option("Asia/Kolkata"),
    local_only: bool = typer.Option(False, "--local-only"),
    redact: bool = typer.Option(False, "--redact"),
    roster: str = typer.Option(
        None,
        help="comma-separated names",
    ),
    speaker: Annotated[
        list[str] | None,
        typer.Option(
            "--speaker",
            help='map labels: --speaker "SPEAKER_00=Priya"',
        ),
    ] = None,
    auto_approve_clean: bool = typer.Option(
        False,
        "--auto-approve-clean",
        help=("approve unflagged high-confidence items without review"),
    ),
    push: str = typer.Option(
        None,
        "--push",
        help="notion|jira (approved items only)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """Extract a transcript into the local store.

    Nothing leaves the machine except LLM calls.
    """
    try:
        d = dt.date.fromisoformat(meeting_date)
    except ValueError:
        _fail("--date must be YYYY-MM-DD")

    smap = dict(s.split("=", 1) for s in (speaker or []) if "=" in s)

    store = _store()

    out = service.ingest(
        path.read_text(
            encoding="utf-8",
            errors="replace",
        ),
        meeting_date=d,
        title=title,
        timezone=tz,
        roster=([r.strip() for r in roster.split(",")] if roster else None),
        speaker_map=smap or None,
        provider=provider,
        local_only=local_only,
        redact=redact,
        store=store,
        on_progress=lambda s, a, b: typer.echo(
            f"\r{s} {a}/{b}",
            nl=False,
        ),
    )

    typer.echo("")

    for w in out.warnings:
        typer.secho(
            f"warning: {w}",
            fg=typer.colors.YELLOW,
        )

    if out.status in ("rejected", "failed"):
        _fail(f"{out.status}: {out.error}")

    typer.echo(f"meeting {out.meeting_id}: {out.status}")

    if out.status == "partial":
        typer.secho(
            "PARTIAL: some chunks failed. Review before trusting this.",
            fg=typer.colors.YELLOW,
        )

    if auto_approve_clean:
        count = service.approve_clean(
            store,
            out.meeting_id,
        )
        typer.echo(f"auto-approved {count} clean items")

    _print_items(store, out.meeting_id)

    typer.echo(f"\nreview:  copilot ui   (open ?meeting={out.meeting_id})")

    if push:
        _do_push(
            store,
            out.meeting_id,
            push,
            dry_run,
        )


def _print_items(store: Store, mid: str) -> None:
    for it in store.items(
        mid,
        "action",
        include_stale=False,
    ):
        if it["status"] == "superseded":
            continue

        typer.echo(
            f"{it['state']:9} "
            f"{it['status']:9} "
            f"{it.get('owner') or '-':10} "
            f"{str(it.get('deadline') or '-'):10} "
            f"{it['title'][:50]:50} "
            f"{','.join(it['flags'])}"
        )


@app.command()
def items(meeting_id: str):
    _print_items(
        _store(),
        meeting_id,
    )


@app.command()
def approve(
    meeting_id: str,
    clean: bool = typer.Option(True, "--clean/--none"),
):
    """Approve every unflagged, high-confidence item."""
    count = service.approve_clean(
        _store(),
        meeting_id,
    )
    typer.echo(f"approved {count} items")


def _do_push(
    store,
    mid,
    target,
    dry_run,
):
    try:
        rep = service.push(
            store,
            mid,
            target,
            dry_run=dry_run,
        )
    except service.ConfigError as e:
        _fail(str(e))

    typer.echo(f"{target}: {rep.summary()}")

    for o in rep.outcomes:
        typer.echo(f"  {o.status:12} {o.item_id} {o.url or ''} {o.error or ''}")

    if rep.orphans:
        typer.secho(
            f"{len(rep.orphans)} previously pushed items "
            "are no longer current: close them manually.",
            fg=typer.colors.YELLOW,
        )


@app.command()
def push(
    meeting_id: str,
    to: str = typer.Option(..., "--to"),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--apply",
    ),
    force: bool = False,
):
    """Push approved items. Dry-run by default; pass --apply to write."""
    _do_push(
        _store(),
        meeting_id,
        to,
        dry_run,
    )


@app.command()
def email(
    meeting_id: str,
    send: bool = typer.Option(False, "--send"),
    force: bool = False,
):
    """Preview or send the summary email to attendees.

    Recipients are listed in roster.json.
    """
    try:
        results = service.email(
            _store(),
            meeting_id,
            send=send,
            force=force,
        )

        for r in results:
            typer.echo(f"{r['status']:10} {r['to']} {r.get('detail', '')}")

    except service.ConfigError as e:
        _fail(str(e))


@app.command()
def slack(meeting_id: str):
    try:
        service.slack(
            _store(),
            meeting_id,
        )
        typer.echo("posted")

    except service.ConfigError as e:
        _fail(str(e))


@app.command()
def ics(
    meeting_id: str,
    out: Annotated[
        Path | None,
        typer.Option("-o"),
    ] = None,
):
    data = service.ics_bytes(
        _store(),
        meeting_id,
    )

    output_path = out or Path(f"{meeting_id}.ics")
    output_path.write_bytes(data)

    typer.echo(f"wrote {output_path}")


@app.command()
def export(meeting_id: str):
    from copilot.digest import to_markdown

    typer.echo(
        to_markdown(
            service.digest(
                _store(),
                meeting_id,
            )
        )
    )


@app.command()
def purge(
    meeting_id: str,
    yes: bool = typer.Option(False, "--yes"),
):
    """Delete a meeting, its transcript and its items from the local store."""
    if not yes and not typer.confirm(f"Delete {meeting_id} permanently?"):
        raise typer.Exit()

    _store().delete_meeting(meeting_id)
    typer.echo("deleted")


@app.command()
def ui():
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(Path(__file__).parent / "ui/app.py"),
        ]
    )


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
):
    import uvicorn

    if host not in ("127.0.0.1", "localhost") and not settings.api_key:
        _fail("Refusing to bind a non-local address without API_KEY set.")

    uvicorn.run(
        "copilot.api.main:app",
        host=host,
        port=port,
    )


@app.command()
def doctor(
    ping: bool = typer.Option(
        False,
        "--ping",
        help="make one cheap call to each configured service",
    ),
):
    """Check configuration. Secrets are never printed."""

    def ok(b: bool):
        typer.secho(
            "ok " if b else "-- ",
            fg=(typer.colors.GREEN if b else typer.colors.YELLOW),
            nl=False,
        )

    provs = service.configured_providers()

    ok(bool(provs))
    typer.echo(f"LLM providers: {provs or 'none configured'}")

    ok(Path(settings.roster_path).exists())
    typer.echo(f"roster file: {settings.roster_path}")

    for name in ("notion", "jira"):
        try:
            target = service.make_target(name)

        except service.ConfigError:
            ok(False)
            typer.echo(f"{name}: not configured")
            continue

        ok(True)

        try:
            detail = f" · {target.check()}" if ping else ""
            typer.echo(f"{name}: configured{detail}")

        except Exception as e:
            typer.secho(
                f"{name}: {type(e).__name__}: {e}",
                fg=typer.colors.RED,
            )

    ok(bool(settings.smtp_host))
    typer.echo(f"smtp: {settings.smtp_host or 'not configured'}")

    ok(bool(settings.slack_webhook_url))
    typer.echo("slack: " + ("configured" if settings.slack_webhook_url else "not configured"))
