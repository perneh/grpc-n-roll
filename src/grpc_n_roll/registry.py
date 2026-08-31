"""Discover gRPC methods from protobuf modules or server reflection."""

from __future__ import annotations

from typing import Any, Iterable

from google.protobuf.descriptor import FileDescriptor, MethodDescriptor, ServiceDescriptor
from google.protobuf.message_factory import GetMessageClass


def new_registry() -> dict[str, Any]:
    return {
        "methods": {},
        # alias -> canonical path, or None when the alias is ambiguous
        "aliases": {},
    }


def method_kind(client_streaming: bool, server_streaming: bool) -> str:
    if client_streaming and server_streaming:
        return "stream_stream"
    if client_streaming:
        return "stream_unary"
    if server_streaming:
        return "unary_stream"
    return "unary_unary"


def aliases_for(spec: dict[str, Any]) -> list[str]:
    service_short = spec["service"].rsplit(".", 1)[-1]
    return [
        spec["path"],
        spec["path"].lstrip("/"),
        f"{spec['service']}.{spec['name']}",
        f"{service_short}/{spec['name']}",
        f"{service_short}.{spec['name']}",
        spec["name"],
    ]


def spec_from_method(service: ServiceDescriptor, method: MethodDescriptor) -> dict[str, Any]:
    client_streaming = method.client_streaming
    server_streaming = method.server_streaming
    return {
        "path": f"/{service.full_name}/{method.name}",
        "service": service.full_name,
        "name": method.name,
        "request_type": GetMessageClass(method.input_type),
        "response_type": GetMessageClass(method.output_type),
        "client_streaming": client_streaming,
        "server_streaming": server_streaming,
        "kind": method_kind(client_streaming, server_streaming),
    }


def register_module(registry: dict[str, Any], module: Any) -> None:
    descriptor = getattr(module, "DESCRIPTOR", None)
    if descriptor is None:
        raise TypeError(f"{module!r} has no protobuf DESCRIPTOR")
    register_file_descriptor(registry, descriptor)


def register_file_descriptor(registry: dict[str, Any], descriptor: FileDescriptor) -> None:
    for service in descriptor.services_by_name.values():
        register_service(registry, service)
    for dependency in descriptor.dependencies:
        if dependency.services_by_name:
            register_file_descriptor(registry, dependency)


def register_service(registry: dict[str, Any], service: ServiceDescriptor) -> None:
    for method in service.methods:
        register_method(registry, spec_from_method(service, method))


def register_method(registry: dict[str, Any], spec: dict[str, Any]) -> None:
    registry["methods"][spec["path"]] = spec
    for alias in aliases_for(spec):
        existing = registry["aliases"].get(alias, spec["path"])
        if existing in (spec["path"], alias):
            registry["aliases"][alias] = spec["path"]
        elif existing != spec["path"]:
            registry["aliases"][alias] = None


def register_reflection(registry: dict[str, Any], channel: Any) -> None:
    try:
        from google.protobuf.descriptor_pool import DescriptorPool
        from grpc_reflection.v1alpha.proto_reflection_descriptor_database import (
            ProtoReflectionDescriptorDatabase,
        )
    except ImportError as exc:
        raise ImportError(
            "Server reflection requires the extra: pip install grpc-n-roll[reflection]"
        ) from exc

    database = ProtoReflectionDescriptorDatabase(channel)
    pool = DescriptorPool(database)
    for name in database.get_services():
        if name.startswith("grpc.reflection."):
            continue
        service = pool.FindServiceByName(name)
        register_service(registry, service)


def resolve(registry: dict[str, Any], path: str) -> dict[str, Any]:
    key = path.strip()
    if key in registry["aliases"]:
        canonical = registry["aliases"][key]
        if canonical is None:
            raise ValueError(
                f"Ambiguous gRPC method {path!r}. Use a full path like /package.Service/Method."
            )
        return registry["methods"][canonical]

    with_slash = key if key.startswith("/") else f"/{key}"
    if with_slash in registry["methods"]:
        return registry["methods"][with_slash]

    available = ", ".join(sorted(registry["methods"])) or "(none registered)"
    raise ValueError(f"Unknown gRPC method {path!r}. Available: {available}")


def paths(registry: dict[str, Any]) -> Iterable[str]:
    return registry["methods"].keys()
