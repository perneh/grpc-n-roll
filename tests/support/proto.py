"""Compile test protos into tests/_generated and put that on sys.path."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_TESTS = Path(__file__).resolve().parent.parent
_GENERATED = _TESTS / "_generated"
_PROTOS = _TESTS / "protos"
_INSTALL_HINT = (
    "grpc_tools is not installed in this Python. "
    "Use the project venv and the dev extra:\n"
    "  python3 -m venv .venv && source .venv/bin/activate\n"
    "  pip install -e \".[dev]\"\n"
    "  pytest tests/integration/test_users.py\n"
    "Or run:  .venv/bin/pytest tests/integration/test_users.py"
)


def _protoc():
    try:
        from grpc_tools import protoc
    except ImportError as exc:
        raise ModuleNotFoundError(_INSTALL_HINT) from exc
    return protoc


def ensure_compiled() -> None:
    _GENERATED.mkdir(exist_ok=True)
    init_file = _GENERATED / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    proto = _PROTOS / "users.proto"
    logger.debug("Compiling %s into %s", proto, _GENERATED)
    rc = _protoc().main(
        [
            "grpc_tools.protoc",
            f"-I{_PROTOS}",
            f"--python_out={_GENERATED}",
            f"--grpc_python_out={_GENERATED}",
            str(proto),
        ]
    )
    if rc != 0:
        logger.error("Failed to compile %s (protoc exit %s)", proto, rc)
        raise RuntimeError(f"Failed to compile {proto}")

    generated = str(_GENERATED)
    if generated not in sys.path:
        sys.path.insert(0, generated)
