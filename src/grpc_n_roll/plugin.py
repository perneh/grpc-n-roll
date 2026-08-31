"""pytest plugin: live-server client fixture and CLI options."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from grpc_n_roll.client import grpc_client


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("grpc-n-roll")
    group.addoption(
        "--grpc-target",
        action="store",
        default=None,
        help="host:port of a live gRPC server for the grpc_live_client fixture",
    )
    group.addoption(
        "--grpc-secure",
        action="store_true",
        default=False,
        help="Use TLS when connecting --grpc-target",
    )


@pytest.fixture
def grpc_live_client(pytestconfig: pytest.Config) -> Iterator[dict[str, Any]]:
    """Client against a running server, discovered via server reflection."""
    live_target = pytestconfig.getoption("--grpc-target")
    if not live_target:
        pytest.skip("pass --grpc-target host:port to run live gRPC tests")
    secure = bool(pytestconfig.getoption("--grpc-secure"))
    with grpc_client(live_target, reflection=True, secure=secure) as client:
        yield client
