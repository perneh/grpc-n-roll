"""Start in-process apps and connect extra clients."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from grpc_n_roll import grpc_app, grpc_client, target

from tests.fakes.user_servicer import UserServicer

logger = logging.getLogger(__name__)


@contextmanager
def serve_users(*, reflection: bool = False) -> Iterator[dict[str, Any]]:
    logger.info("Starting in-process UserService reflection=%s", reflection)
    try:
        with grpc_app(UserServicer(), reflection=reflection) as app:
            yield app
    except Exception:
        logger.error("In-process UserService failed", exc_info=True)
        raise
    logger.info("Stopped in-process UserService")


@contextmanager
def connect_with_protos(app: dict[str, Any], proto_module: Any) -> Iterator[dict[str, Any]]:
    grpc_target = target(app)
    logger.debug("Connecting to %s with explicit protos", grpc_target)
    try:
        with grpc_client(grpc_target, protos=[proto_module]) as client:
            yield client
    except Exception:
        logger.error("Client connection to %s failed", grpc_target, exc_info=True)
        raise


@contextmanager
def connect_with_reflection(app: dict[str, Any]) -> Iterator[dict[str, Any]]:
    grpc_target = target(app)
    logger.debug("Connecting to %s with reflection", grpc_target)
    try:
        with grpc_client(grpc_target, reflection=True) as client:
            yield client
    except Exception:
        logger.error("Reflection client to %s failed", grpc_target, exc_info=True)
        raise
