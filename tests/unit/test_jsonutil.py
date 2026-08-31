"""Tests for proto JSON key mapping — specification-style, functional."""

from tests.support.actions.registry import parse_list_users_request
from tests.support.builders.users import build_list_users


def test_parse_dict_accepts_camel_case_when_json_name_used():
    message = parse_list_users_request(build_list_users(name_prefix_json="Ada"))
    assert message.name_prefix == "Ada"


def test_parse_dict_accepts_snake_case_when_proto_name_used():
    message = parse_list_users_request(build_list_users(name_prefix="Ada"))
    assert message.name_prefix == "Ada"
