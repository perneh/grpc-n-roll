"""Reusable HTTP-shaped assertions with clear failure messages."""

from __future__ import annotations

from typing import Any


def assert_ok(response: dict[str, Any]) -> None:
    assert response["ok"], (
        f"Expected OK, got {response['status_code']} {response['reason']} "
        f"for {response['method']} {response['path']}: {response['text']}"
    )


def assert_status(response: dict[str, Any], status_code: int) -> None:
    actual = response["status_code"]
    assert actual == status_code, (
        f"Expected status {status_code}, got {actual} {response['reason']} "
        f"for {response['method']} {response['path']}: {response['text']}"
    )


def assert_grpc_status_name(response: dict[str, Any], name: str) -> None:
    actual = response["grpc_status_name"]
    assert actual == name, f"Expected grpc_status_name {name!r}, got {actual!r}"


def assert_reason(response: dict[str, Any], reason: str) -> None:
    actual = response["reason"]
    assert actual == reason, f"Expected reason {reason!r}, got {actual!r}"


def assert_path(response: dict[str, Any], path: str) -> None:
    actual = response["path"]
    assert actual == path, f"Expected path {path!r}, got {actual!r}"


def assert_method(response: dict[str, Any], method: str) -> None:
    actual = response["method"]
    assert actual == method, f"Expected method {method!r}, got {actual!r}"


def assert_body_equals(response: dict[str, Any], expected: Any) -> None:
    actual = response["body"]
    assert actual == expected, f"Expected body {expected!r}, got {actual!r}"


def assert_error_message(response: dict[str, Any], fragment: str) -> None:
    message = (response["body"] or {}).get("message", "")
    assert fragment in message, f"Expected {fragment!r} in error message {message!r}"


def assert_header(response: dict[str, Any], key: str, value: str) -> None:
    actual = response["headers"].get(key)
    assert actual == value, f"Expected header {key}={value!r}, got {actual!r}"
