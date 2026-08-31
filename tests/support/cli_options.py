"""Register and resolve --address, --port, and --url. Pure resolvers; no logging."""

from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import urlparse

DEFAULT_ADDRESS = "127.0.0.1"
DEFAULT_PORT = 50051
ENV_ADDRESS = "TEST_ADDRESS"
ENV_PORT = "TEST_PORT"
ENV_URL = "TEST_URL"


def register_options(parser: Any) -> None:
    parser.addoption(
        "--address",
        action="store",
        default=None,
        help="Hostname or IP of the system under test",
    )
    parser.addoption(
        "--port",
        action="store",
        type=int,
        default=None,
        help="TCP port of the system under test",
    )
    parser.addoption(
        "--url",
        action="store",
        default=None,
        help="Full base URL or host:port (overrides --address/--port)",
    )


def parse_port(value: Any, *, source: str) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{source} must be an integer port, got {value!r}") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"{source} must be in 1..65535, got {port}")
    return port


def parse_host_port(url: str) -> tuple[str, int]:
    raw = url.strip()
    if not raw:
        raise ValueError("--url must be a non-empty URL or host:port")
    if "://" not in raw:
        raw = f"grpc://{raw}"
    parsed = urlparse(raw)
    host = parsed.hostname
    if not host:
        raise ValueError(f"Malformed --url: {url!r}")
    if parsed.port is not None:
        return host, parsed.port
    if parsed.scheme == "https":
        return host, 443
    return host, DEFAULT_PORT


def resolve_target(
    address: str | None = None,
    port: int | None = None,
    url: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve host/port with CLI > env > defaults. ``--url`` wins over address/port."""
    env = {} if environ is None else environ

    if url:
        host, parsed_port = parse_host_port(url)
        return _target(host, parsed_port, url=url, source="cli_url", explicit=True)

    if address is not None or port is not None:
        host = address if address is not None else DEFAULT_ADDRESS
        resolved_port = DEFAULT_PORT if port is None else parse_port(port, source="--port")
        return _target(host, resolved_port, source="cli_address_port", explicit=True)

    env_url = env.get(ENV_URL)
    if env_url:
        host, parsed_port = parse_host_port(env_url)
        return _target(host, parsed_port, url=env_url, source="env_url", explicit=True)

    env_address = env.get(ENV_ADDRESS)
    env_port = env.get(ENV_PORT)
    if env_address or env_port:
        host = env_address or DEFAULT_ADDRESS
        resolved_port = (
            parse_port(env_port, source=ENV_PORT) if env_port else DEFAULT_PORT
        )
        return _target(host, resolved_port, source="env_address_port", explicit=True)

    return _target(DEFAULT_ADDRESS, DEFAULT_PORT, source="default", explicit=False)


def _target(
    address: str,
    port: int,
    *,
    source: str,
    explicit: bool,
    url: str | None = None,
) -> dict[str, Any]:
    return {
        "address": address,
        "port": port,
        "url": url or f"grpc://{address}:{port}",
        "grpc_target": f"{address}:{port}",
        "source": source,
        "explicit": explicit,
    }
