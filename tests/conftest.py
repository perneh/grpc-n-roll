"""Shared fixtures only — no assertion helpers."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import pytest

from tests.support.cli_options import register_options, resolve_target
from tests.support.logging_config import configure_logging
from tests.support.proto import ensure_compiled

logger = logging.getLogger(__name__)

_USER_CATALOG = Path(__file__).parent / "support" / "fixtures_data" / "users.json"


def pytest_addoption(parser: pytest.Parser) -> None:
    register_options(parser)


def pytest_configure(config: pytest.Config) -> None:
    configure_logging()
    ensure_compiled()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = str(item.fspath)
        if "/unit/" in path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in path:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session", autouse=True)
def target(pytestconfig: pytest.Config) -> dict[str, Any]:
    resolved = resolve_target(
        address=pytestconfig.getoption("--address"),
        port=pytestconfig.getoption("--port"),
        url=pytestconfig.getoption("--url"),
        environ=os.environ,
    )
    logger.info(
        "Test target %s (grpc %s)",
        resolved["url"],
        resolved["grpc_target"],
    )
    logger.debug("Target source=%s explicit=%s", resolved["source"], resolved["explicit"])
    return resolved


@pytest.fixture(scope="session")
def user_catalog() -> dict[str, dict[str, str]]:
    return json.loads(_USER_CATALOG.read_text())
