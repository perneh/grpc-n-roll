"""pytest plugin that makes gRPC tests read like REST."""

from grpc_n_roll.app import add, grpc_app, target
from grpc_n_roll.client import close, delete, get, grpc_client, patch, post, put, request
from grpc_n_roll.response import GrpcHTTPError, raise_for_status

__all__ = [
    "GrpcHTTPError",
    "add",
    "close",
    "delete",
    "get",
    "grpc_app",
    "grpc_client",
    "patch",
    "post",
    "put",
    "raise_for_status",
    "request",
    "target",
    "__version__",
]
__version__ = "0.1.0"
