"""Shared fixtures for integration tests (real API calls)."""

import pytest
from codex_backend_sdk import CodexClient


def pytest_addoption(parser):
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="run tests that use stored credentials, network access, and account quota",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip_live = pytest.mark.skip(reason="requires explicit --live authorization")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture(scope="session")
def client() -> CodexClient:
    """Authenticated client reused across the whole test session."""
    return CodexClient().authenticate()
