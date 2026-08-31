"""Tests for gRPC to HTTP status mapping — specification-style, functional."""

import pytest
from grpc import StatusCode

from grpc_n_roll.status import http_status_for


@pytest.mark.parametrize(
    "grpc_status,expected",
    [
        (StatusCode.OK, (200, "OK")),
        (StatusCode.NOT_FOUND, (404, "Not Found")),
        (StatusCode.INVALID_ARGUMENT, (400, "Bad Request")),
        (StatusCode.UNAUTHENTICATED, (401, "Unauthorized")),
        (StatusCode.PERMISSION_DENIED, (403, "Forbidden")),
        (StatusCode.ALREADY_EXISTS, (409, "Conflict")),
        (StatusCode.DEADLINE_EXCEEDED, (504, "Gateway Timeout")),
    ],
)
def test_http_status_for_maps_code_when_grpc_status_known(grpc_status, expected):
    assert http_status_for(grpc_status) == expected
