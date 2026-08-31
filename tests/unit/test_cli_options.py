"""Tests for --address/--port/--url resolution — specification-style, functional."""

import pytest

from tests.support.cli_options import (
    DEFAULT_ADDRESS,
    DEFAULT_PORT,
    parse_host_port,
    parse_port,
    resolve_target,
)


def test_resolve_target_uses_defaults_when_nothing_passed():
    target = resolve_target(environ={})
    assert target["address"] == DEFAULT_ADDRESS
    assert target["port"] == DEFAULT_PORT
    assert target["grpc_target"] == f"{DEFAULT_ADDRESS}:{DEFAULT_PORT}"
    assert target["source"] == "default"
    assert target["explicit"] is False


def test_resolve_target_uses_url_when_cli_url_set():
    target = resolve_target(address="ignored", port=1, url="https://staging.example.com:9000")
    assert target["address"] == "staging.example.com"
    assert target["port"] == 9000
    assert target["source"] == "cli_url"
    assert target["explicit"] is True


def test_resolve_target_uses_default_port_when_only_address_given():
    target = resolve_target(address="192.168.1.10", environ={})
    assert target["address"] == "192.168.1.10"
    assert target["port"] == DEFAULT_PORT
    assert target["source"] == "cli_address_port"


def test_resolve_target_uses_env_url_when_cli_empty():
    target = resolve_target(environ={"TEST_URL": "localhost:6000"})
    assert target["grpc_target"] == "localhost:6000"
    assert target["source"] == "env_url"


def test_resolve_target_uses_env_address_port_when_url_missing():
    target = resolve_target(environ={"TEST_ADDRESS": "ci.example.com", "TEST_PORT": "50052"})
    assert target["grpc_target"] == "ci.example.com:50052"
    assert target["source"] == "env_address_port"


def test_parse_port_rejects_value_when_not_numeric():
    with pytest.raises(ValueError, match="TEST_PORT"):
        parse_port("abc", source="TEST_PORT")


def test_parse_host_port_rejects_url_when_host_missing():
    with pytest.raises(ValueError, match="Malformed"):
        parse_host_port("http://")
