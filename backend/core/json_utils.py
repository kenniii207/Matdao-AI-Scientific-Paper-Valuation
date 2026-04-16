"""Utilities for converting complex objects into JSON-serializable structures."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any


def coerce_jsonable(value: Any) -> Any:
    """Best-effort conversion to JSON-serializable Python types.

    - Preserves structure for dict/list where possible.
    - Supports Pydantic (`model_dump`) and common datetime/UUID types.
    - Falls back to `str(value)` for unknown objects.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (uuid.UUID,)):
        return str(value)

    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, dict):
        return {str(k): coerce_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [coerce_jsonable(v) for v in value]

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return coerce_jsonable(model_dump())
        except Exception:
            return str(value)

    as_dict = getattr(value, "dict", None)
    if callable(as_dict):
        try:
            return coerce_jsonable(as_dict())
        except Exception:
            return str(value)

    return str(value)

