"""Orchestrate UserService RPCs. Side effects only; log steps and failures."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from grpc_n_roll import delete, get, patch, post, put

logger = logging.getLogger(__name__)


def _call(label: str, fn, *args: Any, **kwargs: Any) -> dict[str, Any]:
    logger.debug("Starting %s", label)
    try:
        response = fn(*args, **kwargs)
    except Exception:
        logger.error("%s raised", label, exc_info=True)
        raise
    logger.debug("%s status=%s", label, response["status_code"])
    if not response["ok"]:
        logger.error(
            "%s failed: status=%s body=%s",
            label,
            response["status_code"],
            response["text"],
        )
    return response


def user_id_of(response: dict[str, Any]) -> str:
    return response["body"]["id"]


def set_session_header(app: dict[str, Any], key: str, value: str) -> None:
    logger.debug("Set session header %s", key)
    app["headers"][key] = value


def create_user(app: dict[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    return _call("CreateUser", post, app, "CreateUser", json=dict(payload))


def get_user(
    app: dict[str, Any],
    user_id: str,
    *,
    headers: Mapping[str, str] | None = None,
    params: bool = False,
) -> dict[str, Any]:
    if params:
        return _call(
            "GetUser",
            get,
            app,
            "GetUser",
            params={"id": user_id},
            headers=headers,
        )
    return _call(
        "GetUser",
        get,
        app,
        "GetUser",
        json={"id": user_id},
        headers=headers,
    )


def list_users(app: dict[str, Any], query: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return _call("ListUsers", get, app, "ListUsers", json=dict(query or {}))


def update_user(
    app: dict[str, Any],
    payload: Mapping[str, Any],
    *,
    verb: str = "put",
) -> dict[str, Any]:
    caller = patch if verb == "patch" else put
    return _call("UpdateUser", caller, app, "UpdateUser", json=dict(payload))


def delete_user(app: dict[str, Any], user_id: str) -> dict[str, Any]:
    return _call("DeleteUser", delete, app, "DeleteUser", json={"id": user_id})


def import_users(app: dict[str, Any], payloads: list[Mapping[str, Any]]) -> dict[str, Any]:
    return _call("ImportUsers", post, app, "ImportUsers", json=[dict(item) for item in payloads])


def echo_messages(app: dict[str, Any], messages: list[Mapping[str, Any]]) -> dict[str, Any]:
    return _call("Echo", post, app, "Echo", json=[dict(item) for item in messages])


def delay_user(app: dict[str, Any], payload: Mapping[str, Any], *, timeout: float | None) -> dict[str, Any]:
    return _call("Delay", get, app, "Delay", json=dict(payload), timeout=timeout)


def call_method(app: dict[str, Any], path: str, **kwargs: Any) -> dict[str, Any]:
    return _call(path, get, app, path, **kwargs)
