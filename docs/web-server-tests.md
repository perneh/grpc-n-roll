# Tests against the lab web server

This is what happens when pytest is aimed at the running lab (`python -m demo`) instead of an in-process gRPC server.

The lab is two listeners in one process:

| Port | Role |
| --- | --- |
| `8080` | HTTP UI (login, live RPC feed, reset) |
| `50051` | gRPC `UserService` (what the tests call) |

Log in at http://127.0.0.1:8080 with `demo` / `demo` to watch RPCs as tests run. The tests themselves never use the browser; they speak gRPC. The UI is a window onto the same in-memory store.

## How a live run is wired

```bash
python -m demo
pytest tests/integration --url=127.0.0.1:50051
```

`--url` (or `--address`/`--port`, or `TEST_URL`) marks the target as **explicit**. Then the `app` fixture:

1. `POST`s `http://127.0.0.1:8080/reset` with `X-Reset-Key: demo` so the store is empty.
2. Opens a gRPC client with **server reflection** (no compiled `*_pb2` in the test).
3. Yields that client to the same tests that otherwise use `grpc_app(UserServicer())`.

Without `--url`, those tests still run — they start a private in-process server and never touch the lab.

`python -m demo reset` does the same wipe from the CLI. The dashboard **Reset server** button does it while you are logged in.

## What each live test checks

These files use the `app` fixture, so they hit the lab when `--url` is set.

### CRUD — `tests/integration/test_users.py`

Exercises `UserService` as if it were a REST API. After each test the next one resets the lab, so they do not share users.

| Test | RPC(s) | What it proves |
| --- | --- | --- |
| `test_create_user_returns_user_when_name_given` | `CreateUser` | A named user is stored and comes back with an id |
| `test_get_user_returns_created_user_when_id_exists` | `CreateUser`, `GetUser` | Read matches the create body |
| `test_get_user_succeeds_when_short_path_and_params_used` | `CreateUser`, `GetUser` | Short name `GetUser` + `params=` works like a query string |
| `test_get_user_returns_404_when_id_unknown` | `GetUser` | Missing id maps to HTTP 404 / `NOT_FOUND` |
| `test_create_user_returns_400_when_name_missing` | `CreateUser` | Empty name maps to HTTP 400 / `INVALID_ARGUMENT` |
| `test_update_user_changes_name_when_user_exists` | `CreateUser`, `UpdateUser` | Name change persists |
| `test_delete_user_removes_user_when_id_exists` | `CreateUser`, `DeleteUser`, `GetUser` | Delete succeeds; a later get is 404 |
| `test_short_paths_and_verbs_read_like_rest_when_used_together` | create / get / patch / list / delete | One REST-shaped workflow on the live store |

On the dashboard you should see `POST` / `GET` / `PUT` / `DELETE` rows, then a `Reset` at the start of the next test.

### Client behaviour — `tests/integration/test_client.py`

| Test | What it proves on the lab |
| --- | --- |
| `test_get_user_echoes_request_id_when_header_set` | Per-call metadata (`x-request-id`) comes back in trailing headers |
| `test_get_user_echoes_request_id_when_session_header_set` | Session headers on the client are sent on every RPC |
| `test_raise_for_status_returns_response_when_ok` | Successful calls do not raise |
| `test_raise_for_status_raises_when_user_missing` | Failed calls raise only if you opt in |
| `test_delay_maps_to_504_when_deadline_exceeded` | A too-short timeout becomes HTTP 504 / `DEADLINE_EXCEEDED` (`slow`) |
| `test_unknown_method_explains_available_paths_when_path_missing` | A bad path lists methods discovered via reflection |
| `test_list_users_accepts_camel_case_when_json_names_used` | `namePrefix` is accepted as well as `name_prefix` |
| `test_error_response_fields_look_like_http_when_user_missing` | 404 responses still look like HTTP (`reason`, `method`, `path`) |

### Streaming — `tests/integration/test_streaming.py`

| Test | RPC | What it proves |
| --- | --- | --- |
| `test_list_users_returns_json_array_when_name_prefix_matches` | `ListUsers` (server stream) | Stream arrives as a JSON list; prefix `A` keeps Ada and Alan |
| `test_list_users_body_is_iterable_when_users_exist` | `ListUsers` | The body is a list you can iterate |
| `test_import_users_creates_all_when_client_stream_posted` | `ImportUsers` (client stream) | A JSON list is sent as a client stream; `created` is 2 |
| `test_echo_returns_same_messages_when_bidi_stream_posted` | `Echo` (bidi) | Messages come back in order |

### Smoke test — `tests/integration/test_reflection.py`

`test_live_list_users_reaches_server_when_url_given` only runs when a target is explicit (`slow`). It lists users on the lab to prove the client can connect. The other tests in that file start their **own** in-process server (with or without reflection) and do **not** use the lab.

## What you should see in the UI

1. Log in — the live feed is hidden until then.
2. Run pytest with `--url`.
3. **Idle** flips to **Tests running** while RPCs arrive.
4. **Live RPCs** lists method, HTTP-like status, and a short detail (`Ada`, `name is required`, …).
5. **Users** shows the in-memory store; it is often empty again after a delete test or the next test’s reset.
6. **Reset server** leaves a single `200 Reset` row.

## Related

- How to run pytest, markers, and `--url`: [tests/README.md](../tests/README.md)
- Why these RPCs are protobuf on the wire, and how tests still use JSON: [Why gRPC uses protobuf](protobuf.md)
