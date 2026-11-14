import hashlib
import json
import sqlite3
import time
from pathlib import Path

SCHEMA = """CREATE TABLE IF NOT EXISTS calls (
  id INTEGER PRIMARY KEY, ts REAL, run_id TEXT, purpose TEXT, provider TEXT, model TEXT,
  prompt_hash TEXT, latency_s REAL, prompt_tokens INTEGER, completion_tokens INTEGER,
  attempt INTEGER, outcome TEXT, error TEXT, cached INTEGER)"""
COLS = [
    "ts",
    "run_id",
    "purpose",
    "provider",
    "model",
    "prompt_hash",
    "latency_s",
    "prompt_tokens",
    "completion_tokens",
    "attempt",
    "outcome",
    "error",
    "cached",
]


def prompt_hash(messages: list[dict]) -> str:
    return hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()[:16]


class CallLogger:
    """Logs hashes and metadata only, never prompt text (transcripts may be sensitive)."""

    def __init__(self, path: str = "data/calls.sqlite"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._exec(SCHEMA)

    def _exec(self, sql: str, params: tuple = ()):
        conn = sqlite3.connect(self.path, timeout=10)
        try:
            with conn:
                return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def log(self, **row) -> None:
        row.setdefault("ts", time.time())
        vals = tuple(row.get(c) for c in COLS)
        self._exec(
            f"INSERT INTO calls ({','.join(COLS)}) VALUES ({','.join('?' * len(COLS))})",
            vals,
        )

    def summary(self, run_id: str):
        return self._exec(
            "SELECT provider, outcome, COUNT(*), ROUND(AVG(latency_s),2) FROM calls "
            "WHERE run_id=? GROUP BY provider, outcome",
            (run_id,),
        )
