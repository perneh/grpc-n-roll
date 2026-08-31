# Running pytest: host and test selection

Cookbook for this repo. Pick a **host** with `--url` / `--address` / `--port` (or env vars). Pick **which cases** with a path, `-k`, or `-m`. Combine both on one command.

How tests are written: [tests/README.md](../tests/README.md).  
What live cases do on the lab: [Tests against the lab web server](web-server-tests.md).

## Quick start

Install into a venv (the `dev` extra includes `grpcio-tools`, which compiles test protos):

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                             # all tests; in-process gRPC, no extra host
pytest -v                          # show each test name
pytest --collect-only -q           # list collected names, do not run
```

If `pytest` still says `No module named 'grpc_tools'`, that binary is a **system** pytest, not the venv. Use:

```bash
.venv/bin/pytest tests/integration/test_users.py
```

## Choose another host

Without a host flag, integration tests start a private in-process server. Pass a host and they call that gRPC process instead (and `POST` reset on port **8080** on the same address).

| How | Example | When to use |
| --- | --- | --- |
| `--url` | `--url=127.0.0.1:50051` | Full `host:port` or URL (wins over address/port) |
| `--address` + `--port` | `--address=192.168.1.10 --port=50051` | Split host and port |
| `--address` only | `--address=staging.example.com` | Port defaults to **50051** |
| Env | `TEST_URL=10.0.0.8:50051 pytest …` | CI, when flags are awkward |

Precedence: CLI `--url` → CLI `--address`/`--port` → `TEST_URL` → `TEST_ADDRESS`/`TEST_PORT` → default `127.0.0.1:50051` (in-process unless you passed something).

```bash
# Local lab (start it first: python -m demo)
pytest tests/integration --url=127.0.0.1:50051

# Another machine
pytest tests/integration --address=192.168.1.10 --port=50051
pytest tests/integration --url=grpc://staging.example.com:50051

# CI
TEST_URL=10.0.0.8:50051 pytest tests/integration
TEST_ADDRESS=10.0.0.8 TEST_PORT=50051 pytest tests/integration
```

`--url` accepts `host:port`, `http://host:port`, or `grpc://host:port`. The gRPC client uses `host:port` only.

The lab UI stays on **HTTP 8080** on that same host (`DEMO_HTTP_PORT` if you changed it). Live tests reset via `http://<address>:8080/reset`.

### Plugin consumers (`--grpc-target`)

If you use grpc-n-roll in **another** project, the installed plugin exposes `--grpc-target` for the `grpc_live_client` fixture, not `--url`:

```bash
pytest --grpc-target=staging.example.com:50051
pytest --grpc-target=staging.example.com:443 --grpc-secure
```

This repository’s own suite uses `--url` / `--address` / `--port`.

## Choose which test cases to run

Pytest names look like `tests/integration/test_users.py::test_create_user_returns_user_when_name_given`.

### 1. By file or folder

```bash
pytest tests/unit
pytest tests/integration
pytest tests/integration/test_users.py
pytest tests/integration/test_streaming.py tests/integration/test_client.py
```

### 2. By test function (`::`)

```bash
pytest tests/integration/test_users.py::test_get_user_returns_404_when_id_unknown
```

### 3. By substring (`-k`)

`-k` is an expression over the node name. Quotes keep the shell from eating it.

```bash
pytest -k create_user
pytest -k "404 or 400"
pytest -k "user and not delete"
pytest -k "streaming or echo"
```

List matches first:

```bash
pytest --collect-only -q -k create_user
```

### 4. By marker (`-m`)

| Marker | Meaning | Command |
| --- | --- | --- |
| `unit` | No gRPC server | `pytest -m unit` |
| `integration` | Starts a server (in-process, or live if you passed a host) | `pytest -m integration` |
| `slow` | Deadline / live smoke | `pytest -m slow` |

```bash
pytest -m integration
pytest -m "integration and not slow"
pytest -m "unit or integration"
```

Folders are auto-marked `unit` / `integration`. `slow` is set on individual tests.

## Host + selection together

```bash
# CRUD only, against the local lab
python -m demo
pytest tests/integration/test_users.py --url=127.0.0.1:50051

# One case on staging
pytest tests/integration/test_users.py::test_create_user_returns_user_when_name_given \
  --address=staging.example.com --port=50051

# Streaming on another host, skip slow
pytest tests/integration -k "list_users or import or echo" -m "not slow" \
  --url=10.0.0.8:50051

# Everything integration except deadline, local lab
pytest -m "integration and not slow" --url=127.0.0.1:50051
```

## Stock pytest switches (stats and debug)

This repo sets `addopts = --strict-markers --strict-config` in `pyproject.toml`. `-q` and `-v` are **additive**: if both are present they cancel (dots, not names). All flags below are **built-in pytest** — no extra plugins.

Full catalog: `pytest --help`. Pytest docs: [How to use pytest](https://docs.pytest.org/en/stable/how-to/index.html).

### Statistics and timing

| Switch | What it shows | Example |
| --- | --- | --- |
| `-v` / `-vv` | Test names as they run; `-vv` extra fixture/assert detail | `pytest -v` |
| `-ra` | Extra summary of skipped, xfailed, warnings (`a` = all except passed) | `pytest -ra` |
| `-rA` | Same, **including passed** (why each test passed/skipped) | `pytest -rA` |
| `--durations=N` | The **N slowest** tests/setups (0 = all) | `pytest --durations=10` |
| `--durations-min=SECONDS` | Only list items slower than this | `pytest --durations=0 --durations-min=0.05` |
| `--collect-only` / `--co` | What would run, without executing | `pytest --co -q` |
| `--junitxml=PATH` | JUnit XML for CI dashboards | `pytest --junitxml=report.xml` |

```bash
# Slowest ten + skip/xfail reasons (good default “how did the suite do?”)
pytest -v -ra --durations=10

# Everything that took more than 50 ms
pytest --durations=0 --durations-min=0.05 tests/integration
```

`--durations` includes fixture setup/teardown, so a slow `app` fixture shows up even if the test body is tiny.

### Deeper debug

| Switch | What it does | Example |
| --- | --- | --- |
| `--tb=short` | Compact traceback (file:line + assert) | `pytest --tb=short` |
| `--tb=long` | Full traceback with locals at each frame | `pytest --tb=long` |
| `--tb=native` | Standard Python traceback | `pytest --tb=native` |
| `--tb=line` | One line per failure | `pytest --tb=line` |
| `--tb=auto` | Long for the first failure, short after (default-ish) | `pytest --tb=auto` |
| `--full-trace` | Do not cut tracebacks | `pytest --full-trace` |
| `-l` / `--showlocals` | Print local variables at the failing frame | `pytest -l` |
| `-vv` | Verbose asserts (values in comparisons) | `pytest -vv` |
| `-s` / `--capture=no` | Do not capture stdout/stderr (logging, pdb) | `pytest -s` |
| `--show-capture=no` | Hide captured output on failure | `pytest --show-capture=no` |
| `--log-cli-level=LEVEL` | Live log stream while tests run | `pytest --log-cli-level=DEBUG` |
| `--log-cli-level=INFO` | Same, less noisy | `pytest --log-cli-level=INFO` |
| `-x` / `--exitfirst` | Stop on first failure | `pytest -x` |
| `--maxfail=N` | Stop after N failures | `pytest --maxfail=1` |
| `--lf` / `--last-failed` | Re-run only what failed last time | `pytest --lf` |
| `--ff` / `--failed-first` | Failed first, then the rest | `pytest --ff` |
| `--nf` / `--new-first` | New files first | `pytest --nf` |
| `--sw` / `--stepwise` | Stop at failure; next run continues from there | `pytest --sw` |
| `--pdb` | Drop into the debugger on failure | `pytest --pdb -s` |
| `--trace` | Debugger **before** each test | `pytest --trace -s` |
| `--pdbcls=module:cls` | Another debugger (e.g. ipdb) | `pytest --pdbcls=IPython.terminal.debugger:TerminalPdb` |
| `--setup-show` | Fixture setup/teardown order | `pytest --setup-show -v` |
| `--fixtures` | All fixtures pytest knows | `pytest --fixtures` |
| `--fixtures-per-test` | Which fixtures each test uses | `pytest --fixtures-per-test -k create_user` |

This project’s actions log at DEBUG. Pair pytest’s log CLI with `LOG_LEVEL`:

```bash
LOG_LEVEL=DEBUG pytest -vv -l --tb=long --log-cli-level=DEBUG tests/integration/test_users.py
```

One failing test, then inspect:

```bash
pytest -x -vv -l --tb=short --lf
pytest --pdb -s tests/integration/test_users.py::test_get_user_returns_404_when_id_unknown
```

See fixture cost (why `--durations` blamed `app`):

```bash
pytest --setup-show -v tests/integration/test_users.py
```

### Capture vs logging

By default pytest **captures** print/logging and only dumps it on failure. This suite uses `logging`, not `print()`. `-s` turns capture **off**, so anything at WARNING/ERROR on stderr appears even when tests pass.

Non-OK RPCs (404, 400, …) are a normal test outcome here. They are logged at **DEBUG**, not ERROR. You will not see them with a plain `pytest -s`. To watch them live:

```bash
pytest -s --log-cli-level=DEBUG          # stream DEBUG+ live (includes expected 404s)
pytest -s --log-cli-level=WARNING        # repo default; quiet unless something is really wrong
pytest --show-capture=log --tb=short     # on failure, logs only (no stdout noise)
```

### Suggested combos

```bash
# “How is the suite doing?”
pytest -v -ra --durations=10

# “This file is slow / flaky”
pytest -vv -l --tb=short --durations=0 --durations-min=0.02 tests/integration/test_client.py

# “Break on first error and debug”
pytest -x -s --pdb --tb=short

# Last failure only, with logs
LOG_LEVEL=DEBUG pytest --lf -vv -l --log-cli-level=DEBUG

# Inventory
pytest --co -q
pytest --fixtures
pytest --help
```

## Related

- Writing tests and layout: [tests/README.md](../tests/README.md)
- Lab RPCs test-by-test: [web-server-tests.md](web-server-tests.md)
- Why the wire is protobuf: [protobuf.md](protobuf.md)
