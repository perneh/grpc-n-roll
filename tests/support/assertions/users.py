"""Assertions for UserService JSON bodies."""

from __future__ import annotations

from typing import Any

from tests.support.assertions.http import assert_ok


def assert_user_named(response: dict[str, Any], name: str) -> None:
    assert_ok(response)
    actual = response["body"]["name"]
    assert actual == name, f"Expected user name {name!r}, got {actual!r}"


def assert_user_email(response: dict[str, Any], email: str) -> None:
    assert_ok(response)
    actual = response["body"]["email"]
    assert actual == email, f"Expected user email {email!r}, got {actual!r}"


def assert_user_has_id(response: dict[str, Any]) -> None:
    assert_ok(response)
    user_id = response["body"].get("id")
    assert user_id, f"Expected a user id, got {user_id!r}"


def assert_same_user(left: dict[str, Any], right: dict[str, Any]) -> None:
    assert left["body"] == right["body"], (
        f"Expected users to match: {left['body']!r} vs {right['body']!r}"
    )


def assert_user_names(response: dict[str, Any], names: list[str]) -> None:
    assert_ok(response)
    actual = [user["name"] for user in response["body"]]
    assert actual == names, f"Expected names {names!r}, got {actual!r}"
