"""Tests for a second client against an in-process app — specification-style."""

import pytest

from tests.support.actions.app import connect_with_protos, connect_with_reflection, serve_users
from tests.support.actions.registry import compiled_users_pb2
from tests.support.actions.users import create_user, get_user, list_users, user_id_of
from tests.support.assertions.http import assert_ok
from tests.support.assertions.users import assert_user_named, assert_user_names
from tests.support.builders.users import build_user_create


def test_client_lists_users_when_connected_to_app_target():
    with serve_users() as app:
        create_user(app, build_user_create(name="Ada"))
        with connect_with_protos(app, compiled_users_pb2()) as client:
            listed = list_users(client)
            assert_ok(listed)
            assert_user_names(listed, ["Ada"])


def test_reflection_client_fetches_user_when_server_reflection_enabled():
    with serve_users(reflection=True) as app:
        created = create_user(app, build_user_create(name="Ada"))
        with connect_with_reflection(app) as client:
            fetched = get_user(client, user_id_of(created))
            assert_ok(fetched)
            assert_user_named(fetched, "Ada")


@pytest.mark.slow
def test_live_list_users_reaches_server_when_url_given(live_client):
    response = list_users(live_client)
    assert "status_code" in response
