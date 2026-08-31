# grpc-n-roll

A pytest plugin that makes gRPC tests read like REST.

gRPC calls use JSON bodies, HTTP verbs, and HTTP status codes. Assertions look like `httpx` or `requests` tests — no stubs, protobuf constructors, or `RpcError` handling in the test itself.

```python
from grpc_n_roll import post, get

def test_create_user(app):
    response = post(app, "/users.UserService/CreateUser", json={"name": "Ada"})

    assert response["status_code"] == 200
    assert response["body"]["name"] == "Ada"


def test_missing_user_returns_404(app):
    response = get(app, "/users.UserService/GetUser", json={"id": "missing"})

    assert response["status_code"] == 404
```

## Install

```bash
pip install -e ".[dev]"
```

The `dev` extra pulls in `grpcio-tools` (for compiling test protos) and `grpcio-reflection` (for live-server tests).

How to run this repository's tests, including `--address` / `--port` / `--url` and the functional layout, is in [tests/README.md](tests/README.md).

## Docs

- [Tests against the lab web server](docs/web-server-tests.md) — what pytest does when it hits the running lab, test by test.
- [Why gRPC uses protobuf](docs/protobuf.md) — why the wire format is protobuf, and how tests still use JSON.

## Lab web app

A local UserService plus a login UI so you can watch tests hit the server.

```bash
python -m demo
```

Open http://127.0.0.1:8080 and log in with `demo` / `demo`. The dashboard shows live RPCs while tests run. **Reset server** (or `python -m demo reset`) clears users and the event log.

```bash
# Terminal 1
python -m demo

# Terminal 2 — same tests, against the lab
pytest tests/integration --url=127.0.0.1:50051
```

gRPC listens on port 50051. The UI listens on port 8080. Each live test calls `POST /reset` with `X-Reset-Key: demo` so runs start from an empty store.

What those tests check, and what the dashboard should show, is in [Tests against the lab web server](docs/web-server-tests.md).

## Write a fixture

Point `grpc_app` at your generated servicer. The app starts an in-process server and exposes a REST-like client:

```python
# tests/conftest.py
import pytest
from grpc_n_roll import grpc_app
from myapp.users_servicer import UserServicer

@pytest.fixture
def app():
    with grpc_app(UserServicer()) as app:
        yield app
```

`add()` infers `add_*_to_server` and the matching `*_pb2` module from the generated servicer base class. You can pass them explicitly if you prefer:

```python
from grpc_n_roll import add

add(app, UserServicer(), add_UserServiceServicer_to_server, users_pb2)
```

## Call RPCs like HTTP

| REST-style call | gRPC |
| --- | --- |
| `get(app, path, json=...)` / `params=` | unary or server-stream |
| `post(app, path, json=...)` | unary create, or client/bidi stream when `json` is a list |
| `put` / `patch` | unary update |
| `delete` | unary delete |

Paths can be fully qualified or short:

```python
get(app, "/users.UserService/GetUser", json={"id": "1"})
get(app, "users.UserService/GetUser", params={"id": "1"})
get(app, "GetUser", params={"id": "1"})   # unique method name
```

Request bodies are dicts (snake_case proto fields or camelCase JSON names). Streaming RPCs take or return lists:

```python
# server stream → JSON array
users = get(app, "ListUsers", json={"name_prefix": "A"})
assert [user["name"] for user in users["body"]] == ["Ada", "Alan"]

# client stream → POST a list
summary = post(app, "ImportUsers", json=[{"name": "Ada"}, {"name": "Grace"}])
assert summary["body"] == {"created": 2}
```

## Status codes

gRPC statuses are mapped the same way as grpc-gateway, so assertions stay REST-shaped:

| gRPC | `status_code` |
| --- | --- |
| `OK` | 200 |
| `INVALID_ARGUMENT` | 400 |
| `UNAUTHENTICATED` | 401 |
| `PERMISSION_DENIED` | 403 |
| `NOT_FOUND` | 404 |
| `ALREADY_EXISTS` | 409 |
| `DEADLINE_EXCEEDED` | 504 |

The original status is still on the response: `response["grpc_status"]`, `response["grpc_status_name"]`, `response["grpc_code"]`.

Failed calls do **not** raise. Inspect the response, or opt in with `raise_for_status(response)`.

```python
from grpc_n_roll import get

response = get(app, "GetUser", json={"id": "missing"})
assert response["status_code"] == 404
assert "not found" in response["body"]["message"]
```

## Response dict

| Key | Meaning |
| --- | --- |
| `status_code` | HTTP-like status (200, 404, …) |
| `reason` | `OK`, `Not Found`, … |
| `ok` | `True` when the RPC was `OK` |
| `body` | dict for unary, list of dicts for streams |
| `headers` | initial + trailing metadata |
| `text` | pretty-printed JSON |
| `elapsed` | call duration |

Headers work like a REST session:

```python
app["headers"]["authorization"] = "Bearer secret"
response = get(app, "GetUser", params={"id": "1"}, headers={"x-request-id": "req-1"})
```

## Live server

Against an already running process (uses [server reflection](https://grpc.io/docs/guides/reflection/)):

```python
from grpc_n_roll import get, grpc_client

with grpc_client("localhost:50051", reflection=True) as client:
    response = get(client, "/users.UserService/GetUser", json={"id": "1"})
```

Or register protos yourself: `grpc_client("localhost:50051", protos=[users_pb2])`.

The pytest plugin also exposes `--grpc-target` and a `grpc_live_client` fixture:

```bash
pytest --grpc-target localhost:50051
```

```python
from grpc_n_roll import get

def test_live(grpc_live_client):
    response = get(grpc_live_client, "/users.UserService/GetUser", json={"id": "1"})
    assert response["status_code"] == 200
```

## License

Apache License 2.0
