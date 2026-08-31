"""Registry and protobuf helpers used by unit tests."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from grpc_n_roll.jsonutil import parse_dict
from grpc_n_roll.registry import new_registry, register_module, resolve

from tests.support.proto import ensure_compiled

logger = logging.getLogger(__name__)


def compiled_users_pb2():
    ensure_compiled()
    import users_pb2

    return users_pb2


def compiled_users_pb2_grpc():
    ensure_compiled()
    import users_pb2_grpc

    return users_pb2_grpc


def make_user_registry() -> dict[str, Any]:
    logger.debug("Registering users_pb2 methods")
    registry = new_registry()
    register_module(registry, compiled_users_pb2())
    return registry


def resolve_method(registry: dict[str, Any], path: str) -> dict[str, Any]:
    logger.debug("Resolving %s", path)
    try:
        return resolve(registry, path)
    except Exception:
        logger.error("Failed to resolve %s", path, exc_info=True)
        raise


def parse_list_users_request(payload: Mapping[str, Any]):
    module = compiled_users_pb2()
    return parse_dict(dict(payload), module.ListUsersRequest())
