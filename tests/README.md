# Tests

Functional pytest suite for grpc-n-roll. Tests are short specifications that compose builders, actions, and assertions. Diagnostic output uses `logging`, never `print()`.

Cookbook for **another host** and **which cases to run**: [docs/pytest.md](../docs/pytest.md).

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest
pytest tests/unit/test_status.py
pytest tests/integration/test_users.py

# If pytest is not the venv one:
.venv/bin/pytest tests/integration/test_users.py

# Debug logging
LOG_LEVEL=DEBUG pytest
pytest --log-cli-level=DEBUG

# Aim integration/live tests at the lab
python -m demo
pytest tests/integration --url=127.0.0.1:50051

# Stop on first failure (run to fail)
pytest -x
pytest -x tests/integration/test_users.py
```

## Pytest flags

This repo sets `--strict-markers --strict-config` in `pyproject.toml`. These are stock pytest switches. `-q` and `-v` **add together**: a config `-q` plus a CLI `-v` cancel out to dots, not names. There is no `-q` in addopts now, so `-v` shows each test.

| Flag | Long form | What it does |
| --- | --- | --- |
| `-v` | `--verbose` | Print each test name as it runs (`PASSED` / `FAILED`). |
| `-vv` | | Extra verbose: more assertion detail and fixture/setup noise. |
| `-s` | `--capture=no` | Do **not** capture stdout/stderr. Logs and `pdb` print live. Without `-s`, pytest only dumps capture when a test **fails**. |
| `-ra` | `--report-chars=a` | Extra summary at the end: skipped, xfailed, warnings (not passed). |
| `-x` | `--exitfirst` | **Run to fail:** stop on the first failure; do not run the rest. |

```bash
pytest -v tests/integration/test_users.py
pytest -vv tests/integration/test_users.py
pytest -s tests/integration/test_users.py
pytest -ra
pytest -x                                 # run to fail
pytest -x tests/integration

# Typical combo: names + skip reasons + stop at first red
pytest -v -ra -x

# Live logs (expected 404/400 are DEBUG, so they stay hidden unless you raise the log level)
pytest -s --log-cli-level=DEBUG tests/integration/test_users.py
```

`-s` is not a test failure. It only unmutes captured output. More flags (durations, pdb, `--lf`): [docs/pytest.md](../docs/pytest.md).

Without `--url`, integration tests start an in-process gRPC server. With `--url`, they reset the lab (`POST http://<address>:8080/reset`) and call the running gRPC server. Log in at http://127.0.0.1:8080 (`demo` / `demo`) to watch RPCs as tests run. `python -m demo reset` clears the lab from the CLI.

What each live test does on that server: [docs/web-server-tests.md](../docs/web-server-tests.md). Why the wire format is protobuf (and how tests still send JSON): [docs/protobuf.md](../docs/protobuf.md).

## Directory layout

```text
tests/
├── conftest.py                 # shared fixtures, CLI options, logging, proto compile
├── support/
│   ├── logging_config.py       # LOG_LEVEL resolution and logging.basicConfig
│   ├── cli_options.py          # --address, --port, --url (pure resolvers)
│   ├── proto.py                # compile tests/protos into tests/_generated
│   ├── builders/               # pure JSON payloads
│   ├── actions/                # call grpc_app / grpc_client
│   ├── assertions/             # reusable checks with rich messages
│   └── fixtures_data/          # static JSON catalogs
├── unit/                       # no gRPC server
├── integration/                # in-process server (and optional live client)
├── fakes/                      # generated-servicer test double (gRPC requires a class)
└── protos/                     # users.proto
```

## Writing tests

- Name tests `test_<behavior>_when_<condition>`.
- Keep the test body to wiring plus assertion helpers (typically ≤ 10 lines).
- Put shared setup and data in `tests/support/`, not in the test file.
- Prefer `@pytest.mark.parametrize` when the same behavior is checked with different inputs.
- Add a new test function when the behavior or condition is different, not when only data changes.
- Do not put business logic, loops that encode rules, or `pytestconfig` reads in test files.

```python
from tests.support.actions.users import create_user
from tests.support.assertions.users import assert_user_named
from tests.support.builders.users import build_user_create

def test_create_user_returns_user_when_name_given(app):
    response = create_user(app, build_user_create(name="Ada"))
    assert_user_named(response, "Ada")
```

## Support library

| Layer | Put here | Logging |
| --- | --- | --- |
| `builders/` | Pure payloads (`build_user_create`) | No |
| `actions/` | RPC calls and app lifecycle | DEBUG steps; unexpected exceptions at ERROR |
| `assertions/` | `assert_ok`, `assert_user_named`, … | No |
| `cli_options.py` | Parse/resolve target | No |
| `conftest.py` | Fixtures only | Setup/teardown |

Import symbols explicitly (no star imports). If a helper is used by more than one test, it belongs under `tests/support/`.

## Logging

Default level is **WARNING**. Enable DEBUG without code changes:

```bash
LOG_LEVEL=DEBUG pytest
pytest --log-cli-level=DEBUG
```

Format: timestamp, level, logger name, message.

Actions log DEBUG for each RPC (including expected 404/400). Unexpected exceptions are logged at ERROR with `exc_info=True` before re-raising. Do not use `print()`, `pprint()`, or custom debug wrappers.

## CLI options

| Option | Purpose | Example |
| --- | --- | --- |
| `--address` | Hostname or IP | `--address=192.168.1.10` |
| `--port` | TCP port | `--port=50051` |
| `--url` | URL or `host:port` (wins over address/port) | `--url=localhost:50051` |

Precedence: CLI `--url` → CLI `--address`/`--port` → `TEST_URL` → `TEST_ADDRESS`/`TEST_PORT` → `127.0.0.1:50051`.

If only `--address` is given, port defaults to **50051**. Invalid `--port` (non-integer) and malformed `--url` fail fast.

The session fixture `target` exposes `address`, `port`, `url`, `grpc_target`, `source`, and `explicit`. Tests must take `target` (or `live_client`) as an argument — do not read `pytestconfig` in test files.

The library plugin still offers `--grpc-target` for the `grpc_live_client` fixture consumed by downstream projects. This repo's own live tests use `--url` / `--address` / `--port`.

```bash
pytest tests/integration --address=localhost --port=50051
pytest tests/integration --url=http://staging.example.com:9000
TEST_URL=https://ci.example.com:50051 pytest tests/integration
python -m demo && pytest tests/integration --url=127.0.0.1:50051
```

## Markers

| Marker | Meaning | Run |
| --- | --- | --- |
| `unit` | No gRPC server | `pytest -m unit` |
| `integration` | In-process gRPC server | `pytest -m integration` |
| `slow` | Deadlines or live server | `pytest -m slow` |

Directories are auto-marked `unit` / `integration`. Exclude slow tests with `pytest -m "not slow"`.

## CI

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Pass a live host with env vars when CLI flags are awkward:

```bash
TEST_URL=localhost:50051 pytest tests/integration -m slow
```

Coverage and xdist are not in the `dev` extra; add them only if a pipeline needs them. Pytest itself is the test runner.

## Anti-patterns

- Test classes (`class TestFoo`) — use functions and `parametrize`
- Logic-heavy tests — move rules into support functions
- `print()` / `pprint()` — use `logging`
- Shared mutable globals — pass fixtures and return values
- `time.sleep` instead of the RPC `timeout` already under test
- Reading `pytestconfig` inside tests — use the `target` fixture
