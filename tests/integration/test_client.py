"""Tests for client headers, errors, and JSON mapping — specification-style."""

import pytest

from grpc_n_roll import GrpcHTTPError

from tests.support.actions.http import raise_if_error
from tests.support.actions.users import (
    call_method,
    create_user,
    delay_user,
    get_user,
    list_users,
    set_session_header,
    user_id_of,
)
from tests.support.assertions.http import (
    assert_grpc_status_name,
    assert_header,
    assert_method,
    assert_ok,
    assert_path,
    assert_reason,
    assert_status,
)
from tests.support.assertions.users import assert_user_names
from tests.support.builders.users import build_delay, build_list_users, build_user_create


def test_get_user_echoes_request_id_when_header_set(app):
    created = create_user(app, build_user_create(name="Ada"))
    response = get_user(app, user_id_of(created), headers={"x-request-id": "req-123"})
    assert_ok(response)
    assert_header(response, "x-request-id", "req-123")


def test_get_user_echoes_request_id_when_session_header_set(app):
    set_session_header(app, "x-request-id", "session-1")
    created = create_user(app, build_user_create(name="Ada"))
    response = get_user(app, user_id_of(created))
    assert_header(response, "x-request-id", "session-1")


def test_raise_for_status_returns_response_when_ok(app):
    response = create_user(app, build_user_create(name="Ada"))
    assert raise_if_error(response) is response


def test_raise_for_status_raises_when_user_missing(app):
    response = get_user(app, "nope")
    with pytest.raises(GrpcHTTPError, match="404 Not Found"):
        raise_if_error(response)


@pytest.mark.slow
def test_delay_maps_to_504_when_deadline_exceeded(app):
    response = delay_user(app, build_delay(seconds=0.5), timeout=0.05)
    assert_status(response, 504)
    assert_grpc_status_name(response, "DEADLINE_EXCEEDED")


def test_unknown_method_explains_available_paths_when_path_missing(app):
    with pytest.raises(ValueError, match="Unknown gRPC method"):
        call_method(app, "/no.Such/Method")


def test_list_users_accepts_camel_case_when_json_names_used(app):
    create_user(app, build_user_create(name="Ada"))
    create_user(app, build_user_create(name="Grace", email="grace@example.com"))
    response = list_users(app, build_list_users(name_prefix_json="G"))
    assert_user_names(response, ["Grace"])


def test_error_response_fields_look_like_http_when_user_missing(app):
    response = get_user(app, "missing")
    assert_status(response, 404)
    assert_reason(response, "Not Found")
    assert_method(response, "GET")
    assert_path(response, "/users.UserService/GetUser")
