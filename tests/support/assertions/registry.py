"""Assertions for method registry specs."""

from __future__ import annotations

from typing import Any


def assert_method_named(spec: dict[str, Any], name: str) -> None:
    actual = spec["name"]
    assert actual == name, f"Expected method {name!r}, got {actual!r}"


def assert_same_path(left: dict[str, Any], right: dict[str, Any]) -> None:
    assert left["path"] == right["path"], (
        f"Expected path {left['path']!r} to equal {right['path']!r}"
    )
