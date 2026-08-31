"""Test-run logging setup. Default level WARNING; override with LOG_LEVEL."""

from __future__ import annotations

import logging
import os
from typing import Mapping

DEFAULT_LEVEL = "WARNING"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def resolve_log_level(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    return str(env.get("LOG_LEVEL", DEFAULT_LEVEL)).upper()


def configure_logging(
    level: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    resolved = (level or resolve_log_level(environ)).upper()
    numeric = getattr(logging, resolved, None)
    if not isinstance(numeric, int):
        raise ValueError(f"Unknown log level {resolved!r}")
    logging.basicConfig(
        level=numeric,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        force=True,
    )
    return numeric
