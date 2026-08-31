"""Tests for UserService CRUD — specification-style, functional."""

from tests.support.actions.users import (
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
    user_id_of,
)
from tests.support.assertions.http import assert_error_message, assert_ok, assert_status
from tests.support.assertions.users import (
    assert_same_user,
    assert_user_email,
    assert_user_has_id,
    assert_user_named,
    assert_user_names,
)
from tests.support.builders.users import build_user_create, build_user_update, user_from_catalog


def test_create_user_returns_user_when_name_given(app, user_catalog):
    response = create_user(app, user_from_catalog(user_catalog, "ada"))
    assert_user_named(response, "Ada")
    assert_user_email(response, "ada@example.com")
    assert_user_has_id(response)


def test_get_user_returns_created_user_when_id_exists(app):
    created = create_user(app, build_user_create(name="Ada"))
    response = get_user(app, user_id_of(created))
    assert_ok(response)
    assert_same_user(response, created)


def test_get_user_succeeds_when_short_path_and_params_used(app):
    created = create_user(app, build_user_create(name="Ada"))
    response = get_user(app, user_id_of(created), params=True)
    assert_user_named(response, "Ada")


def test_get_user_returns_404_when_id_unknown(app):
    response = get_user(app, "missing")
    assert_status(response, 404)
    assert_error_message(response, "missing")


def test_create_user_returns_400_when_name_missing(app):
    response = create_user(app, build_user_create(name=None, email="nobody@example.com"))
    assert_status(response, 400)
    assert_error_message(response, "name is required")


def test_update_user_changes_name_when_user_exists(app):
    created = create_user(app, build_user_create(name="Ada"))
    response = update_user(app, build_user_update(user_id_of(created), name="Ada Lovelace"))
    assert_user_named(response, "Ada Lovelace")


def test_delete_user_removes_user_when_id_exists(app):
    user_id = user_id_of(create_user(app, build_user_create(name="Ada")))
    deleted = delete_user(app, user_id)
    missing = get_user(app, user_id)
    assert_ok(deleted)
    assert_status(missing, 404)


def test_short_paths_and_verbs_read_like_rest_when_used_together(app):
    created = create_user(app, build_user_create(name="Ada"))
    fetched = get_user(app, user_id_of(created), params=True)
    updated = update_user(
        app, build_user_update(user_id_of(created), email="ada@example.com"), verb="patch"
    )
    listed = list_users(app)
    deleted = delete_user(app, user_id_of(created))
    assert_ok(created)
    assert_ok(fetched)
    assert_user_email(updated, "ada@example.com")
    assert_user_names(listed, ["Ada"])
    assert_ok(deleted)
