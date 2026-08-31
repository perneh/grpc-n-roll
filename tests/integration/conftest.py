"""In-process gRPC app fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from grpc_n_roll.client import grpc_client

from tests.support.actions.app import serve_users
from tests.support.actions.demo import reset_demo


@pytest.fixture
def app(target: dict[str, Any]) -> Iterator[dict[str, Any]]:
    if target["explicit"]:
        reset_demo(target)
        with grpc_client(target["grpc_target"], reflection=True) as client:
            yield client
        return
    with serve_users() as client:
        yield client


@pytest.fixture
def live_client(target: dict[str, Any]) -> Iterator[dict[str, Any]]:
    if not target["explicit"]:
        pytest.skip("pass --url or --address/--port (or TEST_URL) to run live gRPC tests")
    reset_demo(target)
    with grpc_client(target["grpc_target"], reflection=True) as client:
        yield client
