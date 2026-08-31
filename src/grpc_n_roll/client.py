"""REST-like gRPC client used in pytest."""

from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import timedelta
from typing import Any, Iterable, Iterator, Mapping, Sequence

import grpc
from google.protobuf.json_format import ParseError
from google.protobuf.message import Message
from grpc import RpcError

from grpc_n_roll.jsonutil import parse_dict
from grpc_n_roll.registry import new_registry, register_module, register_reflection, resolve
from grpc_n_roll.response import (
    make_request,
    make_response,
    metadata_to_headers,
    response_from_rpc_error,
)


def headers_to_metadata(
    headers: Mapping[str, str] | Sequence[tuple[str, str]] | None,
) -> list[tuple[str, str]]:
    if not headers:
        return []
    if isinstance(headers, Mapping):
        return [(str(key).lower(), str(value)) for key, value in headers.items()]
    return [(str(key).lower(), str(value)) for key, value in headers]


def new_client_state(
    *,
    headers: Mapping[str, str] | None = None,
    protos: Iterable[Any] = (),
    reflection: bool = False,
    channel: grpc.Channel | None = None,
    owns_channel: bool = False,
) -> dict[str, Any]:
    return {
        "headers": dict(headers or {}),
        "registry": new_registry(),
        "channel": channel,
        "owns_channel": owns_channel,
        "protos": list(protos),
        "reflection": reflection,
        "invokers": {},
        "bindings": None,
        "server": None,
        "target": None,
        "executor": None,
        "service_names": [],
        "reflection_enabled": False,
        "max_workers": 8,
        "interceptors": [],
    }


def open_channel(
    target: str,
    *,
    secure: bool,
    options: Sequence[tuple[str, Any]] | None,
) -> grpc.Channel:
    if secure:
        return grpc.secure_channel(target, grpc.ssl_channel_credentials(), options=options)
    return grpc.insecure_channel(target, options=options)


def channel_of(client: dict[str, Any]) -> grpc.Channel:
    channel = client["channel"]
    if channel is None:
        raise RuntimeError("gRPC client has no channel")
    return channel


def ready(client: dict[str, Any]) -> None:
    for proto in client["protos"]:
        register_module(client["registry"], proto)
    if client["reflection"]:
        register_reflection(client["registry"], channel_of(client))


def close(client: dict[str, Any]) -> None:
    if client["owns_channel"] and client["channel"] is not None:
        client["channel"].close()
    client["channel"] = None
    client["invokers"].clear()
    if client["server"] is not None:
        client["server"].stop(grace=0)
        client["server"] = None
    if client["executor"] is not None:
        client["executor"].shutdown(wait=False, cancel_futures=True)
        client["executor"] = None
    client["target"] = None


@contextmanager
def grpc_client(
    target: str | None = None,
    *,
    channel: grpc.Channel | None = None,
    protos: Iterable[Any] = (),
    reflection: bool = False,
    headers: Mapping[str, str] | None = None,
    secure: bool = False,
    options: Sequence[tuple[str, Any]] | None = None,
) -> Iterator[dict[str, Any]]:
    owns_channel = False
    if channel is None and target is not None:
        channel = open_channel(target, secure=secure, options=options)
        owns_channel = True
    client = new_client_state(
        headers=headers,
        protos=protos,
        reflection=reflection,
        channel=channel,
        owns_channel=owns_channel,
    )
    if client["channel"] is not None:
        ready(client)
    try:
        yield client
    finally:
        close(client)


def get(
    client: dict[str, Any],
    path: str,
    json: Any = None,
    *,
    params: dict[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if json:
        body.update(json)
    if params:
        body.update(params)
    return request(client, "GET", path, json=body or None, headers=headers, timeout=timeout)


def post(client: dict[str, Any], path: str, json: Any = None, **kwargs: Any) -> dict[str, Any]:
    return request(client, "POST", path, json=json, **kwargs)


def put(client: dict[str, Any], path: str, json: Any = None, **kwargs: Any) -> dict[str, Any]:
    return request(client, "PUT", path, json=json, **kwargs)


def patch(client: dict[str, Any], path: str, json: Any = None, **kwargs: Any) -> dict[str, Any]:
    return request(client, "PATCH", path, json=json, **kwargs)


def delete(client: dict[str, Any], path: str, json: Any = None, **kwargs: Any) -> dict[str, Any]:
    return request(client, "DELETE", path, json=json, **kwargs)


def request(
    client: dict[str, Any],
    method: str,
    path: str,
    *,
    json: Any = None,
    headers: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    if client["bindings"] is not None:
        from grpc_n_roll.app import ensure_started

        ensure_started(client)
    spec = resolve(client["registry"], path)
    merged_headers = {**client["headers"], **dict(headers or {})}
    http_request = make_request(method.upper(), spec["path"], json, merged_headers)
    metadata = headers_to_metadata(merged_headers)
    started = time.perf_counter()
    try:
        response = invoke(client, spec, json, request=http_request, metadata=metadata, timeout=timeout)
    except RpcError as error:
        elapsed = timedelta(seconds=time.perf_counter() - started)
        return response_from_rpc_error(http_request, error, elapsed)
    response["elapsed"] = timedelta(seconds=time.perf_counter() - started)
    return response


def invoke(
    client: dict[str, Any],
    spec: dict[str, Any],
    payload: Any,
    *,
    request: dict[str, Any],
    metadata: list[tuple[str, str]],
    timeout: float | None,
) -> dict[str, Any]:
    invoker = invoker_for(client, spec)
    if spec["client_streaming"]:
        requests = parse_stream(spec, payload)
    else:
        message = parse_unary(spec, payload)

    if spec["kind"] == "unary_unary":
        proto, call = invoker.with_call(message, metadata=metadata, timeout=timeout)
        return make_response(request=request, message=proto, headers=call_headers(call))
    if spec["kind"] == "unary_stream":
        call = invoker(message, metadata=metadata, timeout=timeout)
        messages = list(call)
        return make_response(
            request=request,
            messages=messages,
            grpc_status=call.code(),
            details=call.details() or "",
            headers=call_headers(call),
        )
    if spec["kind"] == "stream_unary":
        proto, call = invoker.with_call(iter(requests), metadata=metadata, timeout=timeout)
        return make_response(request=request, message=proto, headers=call_headers(call))
    call = invoker(iter(requests), metadata=metadata, timeout=timeout)
    messages = list(call)
    return make_response(
        request=request,
        messages=messages,
        grpc_status=call.code(),
        details=call.details() or "",
        headers=call_headers(call),
    )


def invoker_for(client: dict[str, Any], spec: dict[str, Any]) -> Any:
    cached = client["invokers"].get(spec["path"])
    if cached is not None:
        return cached

    channel = channel_of(client)
    serializer = spec["request_type"].SerializeToString
    deserializer = spec["response_type"].FromString
    if spec["kind"] == "unary_unary":
        invoker = channel.unary_unary(spec["path"], serializer, deserializer)
    elif spec["kind"] == "unary_stream":
        invoker = channel.unary_stream(spec["path"], serializer, deserializer)
    elif spec["kind"] == "stream_unary":
        invoker = channel.stream_unary(spec["path"], serializer, deserializer)
    else:
        invoker = channel.stream_stream(spec["path"], serializer, deserializer)
    client["invokers"][spec["path"]] = invoker
    return invoker


def parse_unary(spec: dict[str, Any], payload: Any) -> Message:
    if payload is None:
        payload = {}
    if not isinstance(payload, Mapping):
        raise TypeError(
            f"{spec['path']} is unary and expects a JSON object, got {type(payload).__name__}"
        )
    return parse_message(spec, payload)


def parse_stream(spec: dict[str, Any], payload: Any) -> list[Message]:
    if payload is None:
        items: list[Any] = []
    elif isinstance(payload, Mapping):
        items = [payload]
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        items = list(payload)
    else:
        raise TypeError(
            f"{spec['path']} is streaming and expects a JSON list or object, "
            f"got {type(payload).__name__}"
        )
    return [parse_message(spec, item) for item in items]


def parse_message(spec: dict[str, Any], payload: Mapping[str, Any]) -> Message:
    try:
        return parse_dict(dict(payload), spec["request_type"]())
    except ParseError as exc:
        raise ValueError(f"Could not build request for {spec['path']}: {exc}") from exc


def call_headers(call: Any) -> dict[str, str]:
    initial = metadata_to_headers(call.initial_metadata())
    trailing = metadata_to_headers(call.trailing_metadata())
    return {**initial, **trailing}
