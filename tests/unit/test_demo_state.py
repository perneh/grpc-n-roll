"""Tests for lab store reset — specification-style, functional."""

from types import SimpleNamespace

from demo.state import new_state, publish, reset_state, snapshot
from grpc import StatusCode


def test_reset_state_clears_users_when_called():
    state = new_state()
    state["users"]["1"] = SimpleNamespace(id="1", name="Ada", email="")
    reset_state(state)
    assert snapshot(state)["user_count"] == 0


def test_publish_appends_event_when_rpc_recorded():
    state = new_state()
    event = publish(
        state,
        method="POST",
        path="/users.UserService/CreateUser",
        grpc_status=StatusCode.OK,
        detail="Ada",
    )
    assert event["status_code"] == 200
    assert snapshot(state)["events"][-1]["detail"] == "Ada"
