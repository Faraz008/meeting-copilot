import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from copilot.config import settings
from copilot.models import ExtractionResult, Meeting, Turn

SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
    id TEXT PRIMARY KEY,
    title TEXT,
    date TEXT NOT NULL,
    timezone TEXT,
    status TEXT NOT NULL,
    roster TEXT NOT NULL DEFAULT '[]',
    turns TEXT NOT NULL DEFAULT '[]',
    report TEXT,
    warnings TEXT,
    error TEXT,
    created REAL,
    updated REAL
);

CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    meeting_id TEXT NOT NULL REFERENCES meetings(id)
        ON DELETE CASCADE,
    kind TEXT NOT NULL,
    data TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending',
    edits TEXT NOT NULL DEFAULT '{}',
    stale INTEGER NOT NULL DEFAULT 0,
    updated REAL
);

CREATE INDEX IF NOT EXISTS ix_items_meeting
ON items(meeting_id, kind);

CREATE TABLE IF NOT EXISTS pushes (
    item_id TEXT NOT NULL,
    target TEXT NOT NULL,
    external_id TEXT,
    url TEXT,
    payload_hash TEXT,
    status TEXT NOT NULL,
    error TEXT,
    updated REAL,
    PRIMARY KEY (item_id, target)
);
"""


KINDS = (
    ("action", "action_items"),
    ("decision", "decisions"),
    ("question", "open_questions"),
    ("followup", "follow_ups"),
)

STATES = {"pending", "approved", "rejected"}

ALLOWED_EDITS = {
    "title",
    "owner",
    "deadline",
    "priority",
    "summary",
    "question",
    "topic",
    "answered",
}

OWNER_FLAGS = {"no_owner", "ambiguous_owner"}

DEADLINE_FLAGS = {
    "no_deadline",
    "unresolved_deadline",
    "ambiguous_deadline",
}


def effective(row) -> dict:
    """Return original extraction combined with human edits.

    Flags resolved by human edits are removed.
    """
    data = json.loads(row["data"])
    edits = json.loads(row["edits"])

    flags = set(data.get("flags", []))

    if edits.get("owner"):
        flags -= OWNER_FLAGS

    if edits.get("deadline"):
        flags -= DEADLINE_FLAGS

    out = {
        **data,
        **edits,
        "flags": sorted(flags),
        "orig": data,
        "kind": row["kind"],
        "state": row["state"],
        "stale": bool(row["stale"]),
        "edited": sorted(edits),
        "meeting_id": row["meeting_id"],
    }

    if "deadline" in edits:
        out["deadline_options"] = []
        out["deadline_time"] = None

    return out


def _first_turn(it: dict) -> int:
    """Return the earliest evidence turn index."""
    return min(
        (evidence["turn_idx"] for evidence in it.get("evidence", [])),
        default=0,
    )


class Store:
    """SQLite persistence layer for meetings and extracted items."""

    def __init__(self, path: str | None = None):
        self.path = Path(path or settings.store_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with self._c() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _c(self):
        """Create and manage a SQLite connection."""
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")

        try:
            with conn:
                yield conn
        finally:
            conn.close()

    # ---------------------------------------------------------
    # Meetings
    # ---------------------------------------------------------

    def begin_meeting(
        self,
        mid: str,
        title: str | None,
        mdate: date,
        tz: str,
    ) -> None:
        """Create a meeting or reset an existing meeting."""
        now = time.time()

        with self._c() as conn:
            conn.execute(
                """
                INSERT INTO meetings (
                    id, title, date, timezone, status,
                    created, updated
                )
                VALUES (?, ?, ?, ?, 'processing', ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = 'processing',
                    title = excluded.title,
                    date = excluded.date,
                    timezone = excluded.timezone,
                    error = NULL,
                    updated = excluded.updated
                """,
                (
                    mid,
                    title,
                    mdate.isoformat(),
                    tz,
                    now,
                    now,
                ),
            )

    def finish_meeting(
        self,
        mid: str,
        status: str,
        *,
        meeting: Meeting | None = None,
        report: dict | None = None,
        warnings: list[str] | None = None,
        error: str | None = None,
    ) -> None:
        """Save meeting results and update processing status."""
        with self._c() as conn:
            if meeting:
                conn.execute(
                    """
                    UPDATE meetings
                    SET roster = ?, turns = ?
                    WHERE id = ?
                    """,
                    (
                        json.dumps(meeting.roster),
                        json.dumps([turn.model_dump() for turn in meeting.turns]),
                        mid,
                    ),
                )

            conn.execute(
                """
                UPDATE meetings
                SET status = ?,
                    report = ?,
                    warnings = ?,
                    error = ?,
                    updated = ?
                WHERE id = ?
                """,
                (
                    status,
                    json.dumps(report or {}, default=str),
                    json.dumps(warnings or []),
                    error,
                    time.time(),
                    mid,
                ),
            )

    def get_meeting(self, mid: str) -> dict | None:
        """Retrieve a meeting by its ID."""
        with self._c() as conn:
            row = conn.execute(
                "SELECT * FROM meetings WHERE id = ?",
                (mid,),
            ).fetchone()

        if not row:
            return None

        data = dict(row)

        for key in ("roster", "turns", "report", "warnings"):
            if data.get(key):
                data[key] = json.loads(data[key])
            elif key == "report":
                data[key] = {}
            else:
                data[key] = []

        return data

    def meeting_obj(self, mid: str) -> Meeting:
        """Return a meeting as a Meeting model."""
        data = self.get_meeting(mid)

        if not data:
            raise KeyError(mid)

        return Meeting(
            meeting_id=mid,
            title=data["title"],
            date=date.fromisoformat(data["date"]),
            timezone=data["timezone"] or "Asia/Kolkata",
            roster=data["roster"],
            turns=[Turn(**turn) for turn in data["turns"]],
        )

    def list_meetings(self) -> list[dict]:
        """Return meetings ordered by most recently updated."""
        with self._c() as conn:
            rows = conn.execute(
                """
                SELECT id, title, date, status, updated
                FROM meetings
                ORDER BY updated DESC
                """
            )

            return [dict(row) for row in rows]

    def delete_meeting(self, mid: str) -> None:
        """Delete a meeting and its associated records."""
        with self._c() as conn:
            ids = [
                row["id"]
                for row in conn.execute(
                    "SELECT id FROM items WHERE meeting_id = ?",
                    (mid,),
                )
            ]

            push_ids = ids + [f"meeting:{mid}"]

            conn.executemany(
                "DELETE FROM pushes WHERE item_id = ?",
                [(item_id,) for item_id in push_ids],
            )

            conn.execute(
                "DELETE FROM items WHERE meeting_id = ?",
                (mid,),
            )

            conn.execute(
                "DELETE FROM meetings WHERE id = ?",
                (mid,),
            )

    # ---------------------------------------------------------
    # Items
    # ---------------------------------------------------------

    def save_extraction(
        self,
        mid: str,
        result: ExtractionResult,
    ) -> None:
        """Upsert extracted items using their stable IDs.

        Existing review states and human edits are preserved.
        Items missing from the new extraction are marked stale
        rather than deleted.
        """
        now = time.time()
        seen = set()

        with self._c() as conn:
            existing = {
                row["id"]
                for row in conn.execute(
                    "SELECT id FROM items WHERE meeting_id = ?",
                    (mid,),
                )
            }

            for kind, attr in KINDS:
                for item in getattr(result, attr):
                    item_id = item.id
                    counter = 0

                    # Handle duplicate IDs within one extraction.
                    while item_id in seen:
                        counter += 1
                        item_id = f"{item.id}x{counter}"

                    seen.add(item_id)

                    data = item.model_copy(update={"id": item_id}).model_dump_json()

                    if item_id in existing:
                        conn.execute(
                            """
                            UPDATE items
                            SET data = ?, stale = 0, updated = ?
                            WHERE id = ?
                            """,
                            (data, now, item_id),
                        )
                    else:
                        conn.execute(
                            """
                            INSERT INTO items (
                                id, meeting_id, kind, data, updated
                            )
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                item_id,
                                mid,
                                kind,
                                data,
                                now,
                            ),
                        )

            # Keep items no longer produced by the extraction.
            for item_id in existing - seen:
                conn.execute(
                    """
                    UPDATE items
                    SET stale = 1, updated = ?
                    WHERE id = ?
                    """,
                    (now, item_id),
                )

    def items(
        self,
        mid: str,
        kind: str | None = None,
        *,
        include_stale: bool = True,
    ) -> list[dict]:
        """Retrieve extracted items for a meeting."""
        query = """
            SELECT *
            FROM items
            WHERE meeting_id = ?
        """

        args = [mid]

        if kind:
            query += " AND kind = ?"
            args.append(kind)

        if not include_stale:
            query += " AND stale = 0"

        with self._c() as conn:
            output = [effective(row) for row in conn.execute(query, args)]

        return sorted(output, key=_first_turn)

    def update_item(
        self,
        item_id: str,
        *,
        state: str | None = None,
        edits: dict | None = None,
    ) -> bool:
        """Update an item's review state or human edits.

        The edits argument replaces the complete edit set.
        The UI should calculate it as a diff against the original.
        """
        if state is not None and state not in STATES:
            raise ValueError(f"bad state {state!r}")

        if edits is not None:
            bad = set(edits) - ALLOWED_EDITS

            if bad:
                raise ValueError(f"fields not editable: {sorted(bad)}")

            if edits.get("deadline"):
                date.fromisoformat(edits["deadline"])

            if edits.get("priority") not in (
                None,
                "high",
                "normal",
                "low",
            ):
                raise ValueError("priority must be high|normal|low")

        sets = ["updated = ?"]
        args = [time.time()]

        if state is not None:
            sets.append("state = ?")
            args.append(state)

        if edits is not None:
            sets.append("edits = ?")
            args.append(json.dumps(edits))

        with self._c() as conn:
            cursor = conn.execute(
                f"""
                UPDATE items
                SET {", ".join(sets)}
                WHERE id = ?
                """,
                args + [item_id],
            )

            return cursor.rowcount > 0

    # ---------------------------------------------------------
    # Pushes
    # ---------------------------------------------------------

    def get_push(
        self,
        item_id: str,
        target: str,
    ) -> dict | None:
        """Retrieve a push record for an item and target."""
        with self._c() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM pushes
                WHERE item_id = ? AND target = ?
                """,
                (item_id, target),
            ).fetchone()

        return dict(row) if row else None

    def record_push(
        self,
        item_id: str,
        target: str,
        external_id: str | None,
        url: str | None,
        payload_hash: str | None,
        status: str,
        error: str | None = None,
    ) -> None:
        """Insert or replace a push record."""
        with self._c() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO pushes (
                    item_id,
                    target,
                    external_id,
                    url,
                    payload_hash,
                    status,
                    error,
                    updated
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    target,
                    external_id,
                    url,
                    payload_hash,
                    status,
                    error,
                    time.time(),
                ),
            )

    def list_pushes(self, mid: str) -> list[dict]:
        """List push records belonging to a meeting."""
        with self._c() as conn:
            rows = conn.execute(
                """
                SELECT p.*
                FROM pushes AS p
                JOIN items AS i ON i.id = p.item_id
                WHERE i.meeting_id = ?

                UNION

                SELECT *
                FROM pushes
                WHERE item_id = ?
                """,
                (mid, f"meeting:{mid}"),
            )

            return [dict(row) for row in rows]
