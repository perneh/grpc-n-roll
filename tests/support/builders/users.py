"""Pure payloads for UserService RPCs."""

from __future__ import annotations

from typing import Any, Mapping


def build_user_create(
    *,
    name: str | None = "Ada",
    email: str | None = "ada@example.com",
) -> dict[str, str]:
    payload: dict[str, str] = {}
    if name is not None:
        payload["name"] = name
    if email is not None:
        payload["email"] = email
    return payload


def build_user_update(user_id: str, *, name: str | None = None, email: str | None = None) -> dict[str, str]:
    payload = {"id": user_id}
    if name is not None:
        payload["name"] = name
    if email is not None:
        payload["email"] = email
    return payload


def build_user_id(user_id: str) -> dict[str, str]:
    return {"id": user_id}


def build_list_users(*, name_prefix: str | None = None, name_prefix_json: str | None = None) -> dict[str, str]:
    if name_prefix_json is not None:
        return {"namePrefix": name_prefix_json}
    if name_prefix:
        return {"name_prefix": name_prefix}
    return {}


def build_delay(*, seconds: float) -> dict[str, float]:
    return {"seconds": seconds}


def build_echo_messages(*values: str) -> list[dict[str, str]]:
    return [{"value": value} for value in values]


def user_from_catalog(catalog: Mapping[str, Mapping[str, Any]], key: str) -> dict[str, Any]:
    return dict(catalog[key])
