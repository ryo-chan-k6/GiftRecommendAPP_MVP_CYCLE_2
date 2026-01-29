from __future__ import annotations

import json
from typing import Any, Mapping

EXCLUDED_KEYS_COMMON = {
    "fetched_at",
    "requested_at",
    "request_id",
    "response_headers",
    "http_status",
    "api_version",
}

SORT_ARRAY_KEYS = {
    "item": {"smallImageUrls", "mediumImageUrls", "tagIds"},
    "ranking": set(),
    "genre": set(),
    "tag": set(),
}


def normalize(entity: str, raw: Mapping[str, Any]) -> Mapping[str, Any]:
    entity_key = entity.lower()
    sort_keys = SORT_ARRAY_KEYS.get(entity_key, set())
    return _normalize_value(raw, sort_keys=sort_keys, parent_key=None)


def _normalize_value(value: Any, *, sort_keys: set[str], parent_key: str | None) -> Any:
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key in sorted(value.keys()):
            if key in EXCLUDED_KEYS_COMMON:
                continue
            normalized[key] = _normalize_value(
                value[key], sort_keys=sort_keys, parent_key=key
            )
        return normalized

    if isinstance(value, list):
        normalized_list = [
            _normalize_value(item, sort_keys=sort_keys, parent_key=parent_key)
            for item in value
        ]
        if parent_key in sort_keys:
            normalized_list.sort(key=_sort_key)
        return normalized_list

    if isinstance(value, str):
        trimmed = value.strip()
        return None if trimmed == "" else trimmed

    return value


def _sort_key(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
    return str(value)
