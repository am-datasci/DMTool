"""Reading YAML and pulling typed fields out of it with useful errors.

Every accessor takes the source path so that a mistake in a content file
reports the file it is actually in.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.errors import ContentError, warning


def read_yaml(path: Path) -> dict:
    """Load a YAML mapping. An empty file is an empty mapping."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ContentError("file not found", path=path) from exc
    except OSError as exc:
        raise ContentError(f"could not be read ({exc.strerror})", path=path) from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        detail = str(exc).replace("\n", " ")
        raise ContentError(f"is not valid YAML — {detail}", path=path) from exc

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ContentError(
            f"should contain a mapping of fields, found {type(data).__name__}",
            path=path,
        )
    return data


def unknown_field_warnings(data: dict, known: set[str], path: Path) -> list[str]:
    """Flag keys we do not recognise.

    A typo'd key would otherwise be silently ignored, which is the
    failure mode most likely to cost an author an evening.
    """
    return [
        warning(f"unrecognised field {key!r} — ignored", path=path)
        for key in sorted(data)
        if key not in known
    ]


def require_str(data: dict, key: str, path: Path) -> str:
    value = data.get(key)
    if value is None:
        raise ContentError("is required but missing", path=path, field=key)
    if not isinstance(value, str) or not value.strip():
        raise ContentError("must be a non-empty string", path=path, field=key)
    return value.strip()


def optional_str(data: dict, key: str, path: Path) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContentError(
            f"must be text, found {type(value).__name__}", path=path, field=key
        )
    value = value.strip()
    return value or None


def optional_int(data: dict, key: str, path: Path) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContentError(
            f"must be a whole number, found {type(value).__name__}",
            path=path,
            field=key,
        )
    return value


def require_int(data: dict, key: str, path: Path) -> int:
    value = optional_int(data, key, path)
    if value is None:
        raise ContentError("is required but missing", path=path, field=key)
    return value


def as_list(data: dict, key: str, path: Path) -> list[Any]:
    value = data.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ContentError(
            f"must be a list, found {type(value).__name__}", path=path, field=key
        )
    return value


def as_str_list(data: dict, key: str, path: Path) -> list[str]:
    items = as_list(data, key, path)
    result = []
    for index, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            raise ContentError(
                f"entry {index + 1} must be a non-empty string",
                path=path,
                field=key,
            )
        result.append(item.strip())
    return result


def as_mapping(value: Any, path: Path, field: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ContentError(
            f"must be a mapping, found {type(value).__name__}", path=path, field=field
        )
    return value


def as_int_mapping(value: Any, path: Path, field: str) -> dict[str, int]:
    mapping = as_mapping(value, path, field)
    result: dict[str, int] = {}
    for key, item in mapping.items():
        if isinstance(item, bool) or not isinstance(item, int):
            raise ContentError(
                f"{key!r} must be a whole number", path=path, field=field
            )
        result[str(key)] = item
    return result
