"""Tests for method discovery — specification-style, functional."""

import pytest

from grpc_n_roll.app import infer_service_binding

from tests.fakes.user_servicer import UserServicer
from tests.support.actions.registry import (
    compiled_users_pb2,
    compiled_users_pb2_grpc,
    make_user_registry,
    resolve_method,
)
from tests.support.assertions.registry import assert_method_named, assert_same_path


@pytest.fixture
def user_registry():
    return make_user_registry()


@pytest.mark.parametrize(
    "path",
    [
        "/users.UserService/GetUser",
        "users.UserService/GetUser",
        "users.UserService.GetUser",
        "UserService/GetUser",
        "GetUser",
    ],
)
def test_registry_resolves_path_when_alias_is_used(path, user_registry):
    canonical = resolve_method(user_registry, "/users.UserService/GetUser")
    spec = resolve_method(user_registry, path)
    assert_method_named(spec, "GetUser")
    assert_same_path(spec, canonical)


def test_infer_servicer_binding_finds_add_fn_when_generated_servicer_used():
    add_fn, proto = infer_service_binding(UserServicer())
    assert add_fn is compiled_users_pb2_grpc().add_UserServiceServicer_to_server
    assert proto is compiled_users_pb2()
