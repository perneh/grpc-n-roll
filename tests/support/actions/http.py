"""Thin adapter around raise_for_status."""

from __future__ import annotations

import logging
from typing import Any

from grpc_n_roll import raise_for_status

logger = logging.getLogger(__name__)


def raise_if_error(response: dict[str, Any]) -> dict[str, Any]:
    logger.debug("raise_for_status path=%s status=%s", response["path"], response["status_code"])
    try:
        return raise_for_status(response)
    except Exception:
        logger.debug(
            "raise_for_status raised for status=%s: %s",
            response["status_code"],
            response["text"],
            exc_info=True,
        )
        raise
