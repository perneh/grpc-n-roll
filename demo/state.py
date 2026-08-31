"""Shared in-memory lab state: users, sessions, and the live event bus."""

from __future__ import annotations

import secrets
import threading
from datetime import datetime, timezone
from itertools import count
from queue import Queue
from typing import Any

from grpc import StatusCode

from grpc_n_roll.status import http_status_for

MAX_EVENTS = 200
SESSION_COOKIE = "demo_session"
DEFAULT_USERNAME = "demo"
DEFAULT_PASSWORD = "demo"


def new_state(*, password: str = DEFAULT_PASSWORD) -> dict[str, Any]:
    return {
        "lock": threading.Lock(),
        "users": {},
        "ids": count(1),
        "events": [],
        "event_seq": count(1),
        "subscribers": [],
        "sessions": {},
        "password": password,
        "username": DEFAULT_USERNAME,
    }


def reset_state(state: dict[str, Any]) -> None:
    with state["lock"]:
        state["users"] = {}
        state["ids"] = count(1)
        state["events"] = []
    publish(
        state,
        method="Reset",
        path="/admin/reset",
        grpc_status=StatusCode.OK,
        detail="Server state cleared",
    )


def snapshot(state: dict[str, Any]) -> dict[str, Any]:
    with state["lock"]:
        users = [
            {"id": user.id, "name": user.name, "email": user.email}
            for user in state["users"].values()
        ]
        events = list(state["events"])
    return {"users": users, "events": events, "user_count": len(users)}


def create_session(state: dict[str, Any], username: str) -> str:
    token = secrets.token_urlsafe(32)
    with state["lock"]:
        state["sessions"][token] = username
    return token


def drop_session(state: dict[str, Any], token: str | None) -> None:
    if not token:
        return
    with state["lock"]:
        state["sessions"].pop(token, None)


def session_user(state: dict[str, Any], token: str | None) -> str | None:
    if not token:
        return None
    with state["lock"]:
        return state["sessions"].get(token)


def credentials_match(state: dict[str, Any], username: str, password: str) -> bool:
    return username == state["username"] and password == state["password"]


def reset_key_matches(state: dict[str, Any], key: str | None) -> bool:
    return bool(key) and key == state["password"]


def subscribe(state: dict[str, Any]) -> Queue:
    subscriber: Queue = Queue()
    with state["lock"]:
        state["subscribers"].append(subscriber)
    return subscriber


def unsubscribe(state: dict[str, Any], subscriber: Queue) -> None:
    with state["lock"]:
        try:
            state["subscribers"].remove(subscriber)
        except ValueError:
            pass


def publish(
    state: dict[str, Any],
    *,
    method: str,
    path: str,
    grpc_status: StatusCode,
    detail: str = "",
) -> dict[str, Any]:
    status_code, reason = http_status_for(grpc_status)
    with state["lock"]:
        event = {
            "id": next(state["event_seq"]),
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "type": "rpc",
            "method": method,
            "path": path,
            "status_code": status_code,
            "reason": reason,
            "ok": grpc_status == StatusCode.OK,
            "detail": detail,
        }
        state["events"].append(event)
        state["events"] = state["events"][-MAX_EVENTS:]
        subscribers = list(state["subscribers"])
    for subscriber in subscribers:
        subscriber.put(event)
    return event
