"""
ChangeSpec 1.0 validation.

Provides a single validate() function that parses a dict or JSON string/bytes
into a typed ChangeSpecEvent, raising ValidationError on invalid input.
"""

from __future__ import annotations

import json
from typing import Union

from pydantic import ValidationError

from .types import ChangeSpecEvent


def validate(raw: Union[dict, str, bytes]) -> ChangeSpecEvent:
    """
    Parse and validate a ChangeSpec 1.0 event.

    Accepts:
      - A dict (e.g. from json.loads())
      - A JSON string
      - JSON bytes

    Returns a ChangeSpecEvent on success.
    Raises pydantic.ValidationError with field-level detail on invalid input.
    Raises json.JSONDecodeError if the input is a string/bytes that is not valid JSON.

    Extension fields (keys starting with 'ext:') are collected into the
    returned event's `extensions` dict. Unknown non-extension fields are
    silently ignored.
    """
    if isinstance(raw, (str, bytes)):
        data = json.loads(raw)
    else:
        data = raw

    return ChangeSpecEvent.model_validate(data)
