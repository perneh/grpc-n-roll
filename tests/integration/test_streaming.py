"""Tests for streaming UserService RPCs — specification-style, functional."""

from tests.support.actions.users import create_user, echo_messages, import_users, list_users
from tests.support.assertions.http import assert_body_equals, assert_ok
from tests.support.assertions.users import assert_user_names
from tests.support.builders.users import build_echo_messages, build_list_users, build_user_create


def test_list_users_returns_json_array_when_name_prefix_matches(app):
    create_user(app, build_user_create(name="Ada"))
    create_user(app, build_user_create(name="Alan"))
    create_user(app, build_user_create(name="Grace"))
    response = list_users(app, build_list_users(name_prefix="A"))
    assert_user_names(response, ["Ada", "Alan"])


def test_list_users_body_is_iterable_when_users_exist(app):
    create_user(app, build_user_create(name="Ada"))
    create_user(app, build_user_create(name="Grace"))
    assert_user_names(list_users(app), ["Ada", "Grace"])


def test_import_users_creates_all_when_client_stream_posted(app):
    response = import_users(
        app,
        [build_user_create(name="Ada"), build_user_create(name="Grace")],
    )
    assert_ok(response)
    assert_body_equals(response, {"created": 2})
    assert_user_names(list_users(app), ["Ada", "Grace"])


def test_echo_returns_same_messages_when_bidi_stream_posted(app):
    response = echo_messages(app, build_echo_messages("ping", "pong"))
    assert_ok(response)
    assert_body_equals(response, [{"value": "ping"}, {"value": "pong"}])
