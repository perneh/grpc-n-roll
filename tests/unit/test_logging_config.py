"""Tests for log level resolution — specification-style, functional."""

import pytest

from tests.support.logging_config import resolve_log_level


@pytest.mark.parametrize(
    "environ,expected",
    [
        ({}, "WARNING"),
        ({"LOG_LEVEL": "DEBUG"}, "DEBUG"),
        ({"LOG_LEVEL": "info"}, "INFO"),
    ],
)
def test_resolve_log_level_reads_env_when_set(environ, expected):
    assert resolve_log_level(environ) == expected
