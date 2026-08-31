"""Accept proto field names (snake_case) and proto3 JSON names (camelCase)."""

from __future__ import annotations

from typing import Any, Mapping

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.json_format import ParseDict
from google.protobuf.message import Message


def _field_for(descriptor: Any, key: str) -> FieldDescriptor | None:
    field = descriptor.fields_by_name.get(key)
    if field is not None:
        return field
    for candidate in descriptor.fields:
        if candidate.json_name == key:
            return candidate
    return None


def to_proto_json(payload: Any, descriptor: Any) -> Any:
    """Rewrite a dict so ParseDict can consume it, regardless of key style."""
    if not isinstance(payload, Mapping) or descriptor is None:
        return payload

    converted: dict[str, Any] = {}
    for key, value in payload.items():
        field = _field_for(descriptor, key)
        json_key = field.json_name if field is not None else key
        if field is None:
            converted[json_key] = value
            continue
        if field.type == FieldDescriptor.TYPE_MESSAGE:
            if field.label == FieldDescriptor.LABEL_REPEATED and isinstance(value, list):
                converted[json_key] = [to_proto_json(item, field.message_type) for item in value]
            elif isinstance(value, Mapping):
                converted[json_key] = to_proto_json(value, field.message_type)
            else:
                converted[json_key] = value
        else:
            converted[json_key] = value
    return converted


def parse_dict(payload: Mapping[str, Any], message: Message) -> Message:
    return ParseDict(to_proto_json(payload, message.DESCRIPTOR), message)
