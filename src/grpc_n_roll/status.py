"""Map gRPC status codes to HTTP-like status codes used in REST tests."""

from __future__ import annotations

from grpc import StatusCode

# Follows the grpc-gateway / Google API HTTP mapping.
GRPC_TO_HTTP: dict[StatusCode, tuple[int, str]] = {
    StatusCode.OK: (200, "OK"),
    StatusCode.CANCELLED: (499, "Client Closed Request"),
    StatusCode.UNKNOWN: (500, "Internal Server Error"),
    StatusCode.INVALID_ARGUMENT: (400, "Bad Request"),
    StatusCode.DEADLINE_EXCEEDED: (504, "Gateway Timeout"),
    StatusCode.NOT_FOUND: (404, "Not Found"),
    StatusCode.ALREADY_EXISTS: (409, "Conflict"),
    StatusCode.PERMISSION_DENIED: (403, "Forbidden"),
    StatusCode.RESOURCE_EXHAUSTED: (429, "Too Many Requests"),
    StatusCode.FAILED_PRECONDITION: (400, "Bad Request"),
    StatusCode.ABORTED: (409, "Conflict"),
    StatusCode.OUT_OF_RANGE: (400, "Bad Request"),
    StatusCode.UNIMPLEMENTED: (501, "Not Implemented"),
    StatusCode.INTERNAL: (500, "Internal Server Error"),
    StatusCode.UNAVAILABLE: (503, "Service Unavailable"),
    StatusCode.DATA_LOSS: (500, "Internal Server Error"),
    StatusCode.UNAUTHENTICATED: (401, "Unauthorized"),
}


def numeric_code(code: StatusCode | int) -> int:
    if isinstance(code, int):
        return code
    value = getattr(code, "value", code)
    if isinstance(value, tuple):
        return int(value[0])
    return int(value)


def as_status_code(code: StatusCode | int) -> StatusCode:
    if isinstance(code, StatusCode):
        return code
    for status in StatusCode:
        if numeric_code(status) == int(code):
            return status
    raise ValueError(f"Unknown gRPC status code: {code!r}")


def http_status_for(code: StatusCode | int) -> tuple[int, str]:
    """Return ``(http_status_code, reason)`` for a gRPC status."""
    grpc_code = as_status_code(code)
    return GRPC_TO_HTTP.get(grpc_code, (500, "Internal Server Error"))
