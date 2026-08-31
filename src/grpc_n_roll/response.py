"""Dict-shaped, REST-like views of gRPC calls."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message
from grpc import StatusCode, RpcError

from grpc_n_roll.status import as_status_code, http_status_for, numeric_code

GrpcHTTPError = type("GrpcHTTPError", (Exception,), {})


def message_to_dict(message: Message) -> dict[str, Any]:
    return MessageToDict(message, preserving_proto_field_name=True)


def metadata_to_headers(metadata: Any) -> dict[str, str]:
    headers: dict[str, str] = {}
    if not metadata:
        return headers
    for key, value in metadata:
        if isinstance(value, bytes):
            headers[key] = value.decode("utf-8", errors="replace")
        else:
            headers[key] = str(value)
    return headers


def make_request(
    method: str,
    path: str,
    payload: Any = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "method": method,
        "path": path,
        "json": payload,
        "headers": headers or {},
    }


def make_response(
    *,
    request: dict[str, Any],
    grpc_status: StatusCode | int = StatusCode.OK,
    message: Message | None = None,
    messages: list[Message] | None = None,
    details: str = "",
    headers: dict[str, str] | None = None,
    elapsed: timedelta | None = None,
) -> dict[str, Any]:
    status = as_status_code(grpc_status)
    status_code, reason = http_status_for(status)
    ok = status == StatusCode.OK
    if not ok:
        body: Any = {"message": details} if details else None
    elif messages is not None:
        body = [message_to_dict(item) for item in messages]
    elif message is None:
        body = None
    else:
        body = message_to_dict(message)
    text = details if body is None else json.dumps(body, indent=2, sort_keys=True)
    return {
        "request": request,
        "path": request["path"],
        "method": request["method"],
        "grpc_status": status,
        "grpc_code": numeric_code(status),
        "grpc_status_name": status.name,
        "status_code": status_code,
        "reason": reason,
        "ok": ok,
        "details": details,
        "headers": headers or {},
        "elapsed": elapsed or timedelta(0),
        "message": message,
        "messages": messages,
        "body": body,
        "text": text,
    }


def response_from_rpc_error(
    request: dict[str, Any],
    error: RpcError,
    elapsed: timedelta,
) -> dict[str, Any]:
    trailing = metadata_to_headers(getattr(error, "trailing_metadata", lambda: ())())
    initial = metadata_to_headers(getattr(error, "initial_metadata", lambda: ())())
    return make_response(
        request=request,
        grpc_status=error.code(),
        details=error.details() or "",
        headers={**initial, **trailing},
        elapsed=elapsed,
    )


def raise_for_status(response: dict[str, Any]) -> dict[str, Any]:
    if not response["ok"]:
        error = GrpcHTTPError(
            f"{response['status_code']} {response['reason']} for {response['path']}: {response['text']}"
        )
        error.response = response
        raise error
    return response
