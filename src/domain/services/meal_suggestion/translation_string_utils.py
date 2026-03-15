"""
String extraction and reconstruction utilities for meal suggestion translation.
Handles path-based traversal of dataclass/dict structures.
"""
from dataclasses import asdict, fields
from enum import Enum
from typing import Any, Dict, List, Tuple


def extract_translatable_strings(obj: Any, path: str = "") -> List[Tuple[str, str]]:
    """
    Recursively extract translatable strings with their paths.

    Args:
        obj: Object to traverse (dataclass, dict, list, etc.)
        path: Current path in the object hierarchy

    Returns:
        List of (path, string) tuples for translatable content
    """
    translatable: List[Tuple[str, str]] = []

    if isinstance(obj, str):
        if obj and not _is_id_path(path):
            translatable.append((path, obj))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            item_path = f"{path}[{i}]" if path else f"[{i}]"
            translatable.extend(extract_translatable_strings(item, item_path))

    elif hasattr(obj, "__dict__"):  # Dataclass or object
        for key, value in obj.__dict__.items():
            if _should_skip_field(key, value):
                continue
            field_path = f"{path}.{key}" if path else key
            translatable.extend(extract_translatable_strings(value, field_path))

    elif isinstance(obj, dict):
        for key, value in obj.items():
            if _should_skip_field(key, value):
                continue
            field_path = f"{path}.{key}" if path else key
            translatable.extend(extract_translatable_strings(value, field_path))

    return translatable


def reconstruct_with_translations(obj: Any, translation_map: Dict[str, str]) -> Any:
    """
    Reconstruct object with translated strings applied via path map.

    Args:
        obj: Original object to reconstruct
        translation_map: Mapping from path to translated string

    Returns:
        New object with translated content
    """
    if hasattr(obj, "__dataclass_fields__"):
        obj_dict = asdict(obj)
    elif isinstance(obj, dict):
        obj_dict = obj.copy()
    else:
        return obj

    for path, translated_value in translation_map.items():
        _set_nested_value(obj_dict, path, translated_value)

    if hasattr(obj, "__dataclass_fields__"):
        return _dict_to_dataclass(obj_dict, type(obj))
    return obj_dict


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _should_skip_field(key: str, value: Any) -> bool:
    """Return True if the field should be excluded from translation."""
    if key.endswith("_id") or key == "id":
        return True
    if isinstance(value, (int, float, bool, type(None))):
        return True
    if isinstance(value, Enum):
        return True
    if hasattr(value, "isoformat"):  # datetime-like
        return True
    return False


def _is_id_path(path: str) -> bool:
    """Return True if the path represents an ID field."""
    return path.endswith("_id") or path.endswith(".id") or path == "id"


def _set_nested_value(obj_dict: dict, path: str, value: Any) -> None:
    """Set a value in a nested dict using a dot/bracket path string."""
    parts = _parse_path(path)
    if not parts:
        return

    current = obj_dict
    for part in parts[:-1]:
        if isinstance(part, int):
            if isinstance(current, list) and 0 <= part < len(current):
                current = current[part]
            else:
                return
        else:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return

    last_part = parts[-1]
    if isinstance(last_part, int):
        if isinstance(current, list) and 0 <= last_part < len(current):
            current[last_part] = value
    else:
        if isinstance(current, dict) and last_part in current:
            current[last_part] = value


def _parse_path(path: str) -> List[Any]:
    """Parse a path string into a list of keys (str) and indices (int)."""
    parts: List[Any] = []
    current_key = ""
    i = 0

    while i < len(path):
        if path[i] == "[":
            if current_key:
                parts.append(current_key)
                current_key = ""
            j = i + 1
            while j < len(path) and path[j] != "]":
                j += 1
            if j < len(path):
                index_str = path[i + 1: j]
                try:
                    parts.append(int(index_str))
                except ValueError:
                    return []
                i = j + 1
        elif path[i] == ".":
            if current_key:
                parts.append(current_key)
                current_key = ""
            i += 1
        else:
            current_key += path[i]
            i += 1

    if current_key:
        parts.append(current_key)

    return parts


def _dict_to_dataclass(obj_dict: dict, dataclass_type: type) -> Any:
    """Convert a dict back to a dataclass instance, handling nested structures."""
    if not hasattr(dataclass_type, "__dataclass_fields__"):
        return obj_dict

    field_values = {}
    for field in fields(dataclass_type):
        field_name = field.name
        if field_name not in obj_dict:
            continue
        value = obj_dict[field_name]
        if hasattr(field.type, "__dataclass_fields__"):
            field_values[field_name] = _dict_to_dataclass(value, field.type)
        elif (
            hasattr(field.type, "__origin__")
            and field.type.__origin__ is list
            and hasattr(field.type.__args__[0], "__dataclass_fields__")
        ):
            item_type = field.type.__args__[0]
            field_values[field_name] = [
                _dict_to_dataclass(item, item_type) for item in value
            ]
        else:
            field_values[field_name] = value

    return dataclass_type(**field_values)
