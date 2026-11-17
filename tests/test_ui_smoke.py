from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")

APP_PATH = Path(__file__).resolve().parents[1] / "src" / "copilot" / "ui" / "app.py"


def test_app_renders_empty_and_with_meeting(tmp_path, monkeypatch):
    from copilot.config import settings
    from copilot.store import Store
    from tests.helpers import seed

    monkeypatch.setattr(settings, "store_path", str(tmp_path / "ui.sqlite"))

    at = st_testing.AppTest.from_file(str(APP_PATH), default_timeout=30).run()

    assert not at.exception

    seed(Store(), 2)

    at = st_testing.AppTest.from_file(str(APP_PATH), default_timeout=30)
    at.query_params["meeting"] = "m1"
    at.run()

    assert not at.exception
