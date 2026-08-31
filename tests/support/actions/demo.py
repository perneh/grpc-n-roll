"""Reset the demo lab HTTP server before live tests."""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def reset_demo(target: dict[str, Any], *, http_port: str | None = None, password: str | None = None) -> None:
    port = http_port or os.environ.get("DEMO_HTTP_PORT", "8080")
    key = password or os.environ.get("DEMO_PASSWORD", "demo")
    url = f"http://{target['address']}:{port}/reset"
    logger.debug("Resetting lab at %s", url)
    request = Request(url, data=b"", method="POST", headers={"X-Reset-Key": key})
    try:
        with urlopen(request, timeout=2) as response:
            body = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        logger.error("Lab reset failed at %s", url, exc_info=True)
        raise RuntimeError(
            f"Could not reset the lab at {url}. Start it with: python -m demo"
        ) from exc
    logger.info("Lab reset ok user_count=%s", body.get("user_count"))
