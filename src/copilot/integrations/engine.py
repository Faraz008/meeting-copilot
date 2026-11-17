from copilot.integrations.base import Outcome, PushItem, Target
from copilot.integrations.http import AuthError, NotFound
from copilot.llm.redact import redact
from copilot.store import Store


def push_items(
    store: Store,
    target: Target,
    items: list[PushItem],
    *,
    dry_run: bool = False,
    force: bool = False,
) -> list[Outcome]:
    """Per item:
    unchanged -> skip;
    known external id -> update (recreate if it vanished);
    unknown -> look it up by our id (crash recovery) -> else create.

    One failure never stops the rest, except an auth failure,
    which would fail every remaining item identically.
    """
    out: list[Outcome] = []
    aborted = False
    for it in items:
        if aborted:
            out.append(
                Outcome(it.id, target.name, "skipped", error="aborted: authentication failed")
            )
            continue
        fp = it.fingerprint()
        rec = store.get_push(it.id, target.name)
        try:
            if rec and rec["status"] == "ok" and rec["payload_hash"] == fp and not force:
                out.append(Outcome(it.id, target.name, "unchanged", rec["external_id"], rec["url"]))
                continue
            if dry_run:
                out.append(
                    Outcome(
                        it.id,
                        target.name,
                        "would_update" if rec and rec["external_id"] else "would_create",
                        rec["external_id"] if rec else None,
                    )
                )
                continue
            if rec and rec["external_id"]:
                try:
                    url, ext, status = (
                        target.update(rec["external_id"], it),
                        rec["external_id"],
                        "updated",
                    )
                except NotFound:  # deleted or archived remotely
                    ext, url = target.create(it)
                    status = "created"
                url = url or rec["url"]
            else:
                found = target.find(it.id)
                if found:
                    ext, url = found
                    target.update(ext, it)
                    status = "updated"
                else:
                    ext, url = target.create(it)
                    status = "created"
            store.record_push(it.id, target.name, ext, url, fp, "ok")
            out.append(Outcome(it.id, target.name, status, ext, url))
        except AuthError as e:
            aborted = True
            err = redact(str(e))[:300]
            store.record_push(
                it.id,
                target.name,
                rec["external_id"] if rec else None,
                rec["url"] if rec else None,
                fp,
                "failed",
                err,
            )
            out.append(Outcome(it.id, target.name, "failed", error=err))
        except Exception as e:
            err = redact(f"{type(e).__name__}: {e}")[:300]
            store.record_push(
                it.id,
                target.name,
                rec["external_id"] if rec else None,
                rec["url"] if rec else None,
                fp,
                "failed",
                err,
            )
            out.append(Outcome(it.id, target.name, "failed", error=err))
    return out
