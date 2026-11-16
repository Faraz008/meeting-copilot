import pytest


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", help="run tests that hit real LLM providers")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip = pytest.mark.skip(reason="needs --live")
    for it in items:
        if "live" in it.keywords:
            it.add_marker(skip)
