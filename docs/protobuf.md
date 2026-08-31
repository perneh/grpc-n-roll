# Why gRPC uses protobuf — and how to work without writing it

gRPC’s default payload is [Protocol Buffers](https://protobuf.dev/) (protobuf): a `.proto` schema, a compact binary encoding, and generated stubs per language. This repo’s lab still speaks protobuf on the wire. Tests and the dashboard do not: they send and show JSON. This page is why the wire format is protobuf, and which ways you can avoid touching it.

## What protobuf is for

A `.proto` file is the contract. `tests/protos/users.proto` declares messages (`User`, `CreateUserRequest`, …) and the `UserService` RPCs, including which calls are streams.

From that file, `protoc` generates:

- `*_pb2.py` — message classes (`User`, `GetUserRequest`, …)
- `*_pb2_grpc.py` — service stubs and `add_*_to_server`

gRPC then sends **binary protobuf**, not JSON, over HTTP/2. Field numbers (`string name = 2`) are what go on the wire, not the field names.

## Why gRPC chose it

| Need | What protobuf gives |
| --- | --- |
| Small, fast payloads | Binary, length-delimited fields; cheaper than JSON for high QPS |
| A typed contract | The `.proto` is the source of truth for every language |
| Compatibility | New fields with new numbers; old clients ignore what they do not know |
| Code generation | Stubs in Python, Go, Java, … from one file |
| Streaming | Same messages for unary, server-stream, client-stream, and bidi |

JSON-over-HTTP can do APIs. It does not by itself give a single schema, generated stubs, field-number compatibility, or first-class streams the way gRPC + protobuf does.

## You still need *a* schema on the wire

gRPC does not require *you* to construct protobuf objects in tests. It does require that **something** encode and decode them: generated code, reflection + a descriptor, or a proxy that transcodes JSON to protobuf.

grpc-n-roll sits in that gap:

```text
test JSON dict  →  parse_dict / protobuf message  →  gRPC bytes
gRPC bytes      →  protobuf message              →  response["body"] JSON
```

That is why `post(app, "CreateUser", json={"name": "Ada"})` never mentions `users_pb2.User`. The library builds the message from the method descriptor (from a compiled module **or** [server reflection](https://grpc.io/docs/guides/reflection/)).

Live lab tests use reflection: the running server publishes its descriptors, so pytest does not import `*_pb2` at all.

## Ways to avoid protobuf in *your* code

### 1. JSON in tests (this library)

Keep protobuf on the server. In tests, use dicts, HTTP verbs, and HTTP-like status codes. Snake_case proto names and camelCase JSON names both work (`name_prefix` / `namePrefix`).

This is the path the lab tests take. See [Tests against the lab web server](web-server-tests.md).

### 2. Server reflection (no compiled stubs on the client)

If the server enables reflection, a client can ask “which methods exist?” and “what does this message look like?” and still send protobuf bytes. `grpc_client(..., reflection=True)` does that. The lab turns reflection on so `--url` tests do not need `users_pb2`.

You still need `protoc` **on the server** (or a language that compiles `.proto` at build time). The client skips codegen.

### 3. gRPC-JSON transcoding / grpc-gateway

Put a reverse proxy in front of gRPC that accepts REST+JSON and transcodes to protobuf. The browser or `httpx` never sees gRPC. The backend is still protobuf.

Useful when some clients must stay HTTP/JSON. It is another hop, and streaming mappings are limited compared with native gRPC.

### 4. Connect, gRPC-Web, and JSON payloads

[Connect](https://connectrpc.com/) and gRPC-Web can speak protobuf **or** JSON over HTTP/1.1 or HTTP/2. The schema is still usually `.proto`. You drop the binary encoding in the browser, not the contract.

### 5. Drop gRPC and use JSON HTTP

A normal REST (or JSON-RPC) service has no protobuf and no gRPC. You lose generated cross-language stubs, binary efficiency, and gRPC streams unless you rebuild them.

That is a product choice, not a gRPC feature. This repo exists for teams that **keep** gRPC in production and want REST-shaped tests.

### 6. Other encodings (uncommon)

gRPC can theoretically carry other payloads (custom codecs). In practice almost everyone uses protobuf. FlatBuffers, Cap’n Proto, or raw JSON inside a `bytes` field are possible but you give up the standard tooling.

## What you cannot skip if you stay on gRPC

- A **service definition** (almost always `.proto`).
- **Something** that turns that definition into serializers (codegen or reflection).
- HTTP/2 (or a gateway that hides it).

You *can* skip: writing `users_pb2.User(name="Ada")` in tests, checking in generated `*_pb2.py` for the test client, and asserting on `grpc.RpcError` instead of `status_code == 404`.

## In this repository

| Layer | Format |
| --- | --- |
| `tests/protos/users.proto` | Schema |
| Lab gRPC port `50051` | Binary protobuf |
| Lab UI / pytest bodies | JSON dicts |
| Live tests with `--url` | Reflection; no client-side `*_pb2` import |

## Related

- Lab tests and what they prove: [Tests against the lab web server](web-server-tests.md)
- Running pytest: [tests/README.md](../tests/README.md)
