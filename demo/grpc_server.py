"""gRPC UserService with server reflection."""

from __future__ import annotations

import logging
from concurrent import futures
from typing import Any

import grpc
from grpc_reflection.v1alpha import reflection

from demo.servicer import UserServicer
from tests.support.proto import ensure_compiled

logger = logging.getLogger(__name__)


def start_grpc(state: dict[str, Any], host: str, port: int) -> grpc.Server:
    ensure_compiled()
    import users_pb2
    import users_pb2_grpc

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    users_pb2_grpc.add_UserServiceServicer_to_server(UserServicer(state), server)
    service_names = (
        users_pb2.DESCRIPTOR.services_by_name["UserService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)
    bound = server.add_insecure_port(f"{host}:{port}")
    if not bound:
        raise RuntimeError(f"Failed to bind gRPC server on {host}:{port}")
    server.start()
    logger.info("gRPC listening on %s:%s", host, bound)
    return server
