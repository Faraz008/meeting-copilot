from datetime import date

import pytest

from copilot.extract.safe import run_safe
from copilot.io import ROOT
from copilot.llm.factory import build_router

pytestmark = pytest.mark.live


def test_real_provider_roundtrip_on_s01():
    raw = (ROOT / "data/synthetic/s01.txt").read_text(encoding="utf-8")
    r = run_safe(
        raw,
        build_router(cache_mode="off"),
        meeting_id="s01",
        meeting_date=date(2025, 3, 12),
    )
    assert r.status in {"ok", "partial"} and r.result.action_items
    assert all(i.evidence for i in r.result.action_items)
