"""In-process gRPC test app, similar to a REST TestClient."""

from __future__ import annotations

import inspect
import importlib
from concurrent import futures
from contextlib import contextmanager
from typing import Any, Callable, Iterator

import grpc

from grpc_n_roll.client import close, new_client_state, ready


def infer_service_binding(servicer: object) -> tuple[Callable[..., None], Any]:
    """Find ``add_*_to_server`` and the matching ``*_pb2`` module for a servicer."""
    for cls in type(servicer).__mro__:
        module = inspect.getmodule(cls)
        if module is None:
            continue
        add_fn = getattr(module, f"add_{cls.__name__}_to_server", None)
        if add_fn is None:
            continue
        pb2_name = module.__name__.replace("_grpc", "")
        if pb2_name == module.__name__:
            continue
        return add_fn, importlib.import_module(pb2_name)
    raise TypeError(
        f"Could not infer gRPC service from {type(servicer).__name__}. "
        "Pass add_to_server and proto_module explicitly."
    )


@contextmanager
def grpc_app(
    *servicers: object,
    reflection: bool = False,
    max_workers: int = 8,
    headers: dict[str, str] | None = None,
    interceptors: list[Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Start servicers in-process and call them with a REST-like client.

    Typical pytest fixture::

        @pytest.fixture
        def app():
            with grpc_app(UserServicer()) as app:
                yield app
    """
    app = new_client_state(headers=headers)
    app["bindings"] = []
    app["reflection_enabled"] = reflection
    app["max_workers"] = max_workers
    app["interceptors"] = interceptors or []
    for servicer in servicers:
        add(app, servicer)
    try:
        yield app
    finally:
        close(app)


def add(
    app: dict[str, Any],
    servicer: object,
    add_to_server: Callable[..., None] | None = None,
    proto_module: Any = None,
) -> dict[str, Any]:
    if app["server"] is not None:
        raise RuntimeError("Cannot add services after the server has started")
    if add_to_server is None or proto_module is None:
        inferred_add, inferred_proto = infer_service_binding(servicer)
        add_to_server = add_to_server or inferred_add
        proto_module = proto_module or inferred_proto
    app["bindings"].append((add_to_server, servicer, proto_module))
    app["protos"].append(proto_module)
    descriptor = getattr(proto_module, "DESCRIPTOR", None)
    if descriptor is not None:
        for service in descriptor.services_by_name.values():
            app["service_names"].append(service.full_name)
    return app


def target(app: dict[str, Any]) -> str:
    ensure_started(app)
    assert app["target"] is not None
    return app["target"]


def ensure_started(app: dict[str, Any]) -> None:
    if app["server"] is not None:
        return
    if not app["bindings"]:
        raise RuntimeError("grpc_app has no services; call add() before making requests")

    app["executor"] = futures.ThreadPoolExecutor(max_workers=app["max_workers"])
    if app["interceptors"]:
        app["server"] = grpc.server(app["executor"], interceptors=app["interceptors"])
    else:
        app["server"] = grpc.server(app["executor"])

    for add_to_server, servicer, _proto in app["bindings"]:
        add_to_server(servicer, app["server"])

    if app["reflection_enabled"]:
        enable_reflection(app)

    port = app["server"].add_insecure_port("127.0.0.1:0")
    if not port:
        raise RuntimeError("Failed to bind gRPC test server")
    app["server"].start()
    app["target"] = f"127.0.0.1:{port}"
    app["channel"] = grpc.insecure_channel(app["target"])
    app["owns_channel"] = True
    ready(app)


def enable_reflection(app: dict[str, Any]) -> None:
    try:
        from grpc_reflection.v1alpha import reflection
    except ImportError as exc:
        raise ImportError(
            "Server reflection requires the extra: pip install grpc-n-roll[reflection]"
        ) from exc
    names = tuple(dict.fromkeys(app["service_names"])) + (reflection.SERVICE_NAME,)
    reflection.enable_server_reflection(names, app["server"])
