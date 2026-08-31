"""Run the lab UI + gRPC UserService, or reset a running lab."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from demo.grpc_server import start_grpc
from demo.http_server import start_http
from demo.state import DEFAULT_PASSWORD, new_state

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="grpc-n-roll lab web + gRPC server")
    parser.add_argument("command", nargs="?", choices=["reset"], help="reset a running lab")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=int(os.environ.get("DEMO_HTTP_PORT", "8080")))
    parser.add_argument("--grpc-port", type=int, default=int(os.environ.get("DEMO_GRPC_PORT", "50051")))
    parser.add_argument(
        "--password",
        default=os.environ.get("DEMO_PASSWORD", DEFAULT_PASSWORD),
        help="login password and X-Reset-Key (default: demo)",
    )
    return parser


def reset_lab(host: str, http_port: int, password: str) -> None:
    url = f"http://{host}:{http_port}/reset"
    request = urllib.request.Request(
        url,
        data=b"",
        method="POST",
        headers={"X-Reset-Key": password},
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reset lab at {url}: {exc}") from exc
    logger.info("Reset ok: %s users", body.get("user_count"))
    print(f"Reset {url} — {body.get('user_count', 0)} users")


def serve(host: str, http_port: int, grpc_port: int, password: str) -> None:
    state = new_state(password=password)
    grpc_server = start_grpc(state, host, grpc_port)
    http_server: ThreadingHTTPServer = start_http(state, host, http_port)
    thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    thread.start()
    print(f"Lab UI   http://{host}:{http_port}  (login demo / {password})")
    print(f"gRPC     {host}:{grpc_port}")
    print("Reset    python -m demo reset")
    print(f"Tests    pytest tests/integration --url={host}:{grpc_port}")
    sys.stdout.flush()
    try:
        grpc_server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        http_server.shutdown()
        grpc_server.stop(grace=0)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = build_parser().parse_args(argv)
    if args.command == "reset":
        reset_lab(args.host, args.http_port, args.password)
        return
    serve(args.host, args.http_port, args.grpc_port, args.password)


if __name__ == "__main__":
    main(sys.argv[1:])
