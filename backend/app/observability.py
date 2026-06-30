from __future__ import annotations

import json
import logging
from typing import Any, Optional


PIPELINE_LOGGER_NAME = "web2audio.pipeline"


def configure_logging(log_level: str = "INFO") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger(PIPELINE_LOGGER_NAME).setLevel(level)


def _format_log_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if not text:
        return '""'
    if any(character.isspace() for character in text):
        return json.dumps(text, ensure_ascii=False)
    return text


def log_pipeline_event(
    event: str,
    stage: str,
    *,
    level: int = logging.INFO,
    exc_info: Optional[bool] = None,
    **fields: Any,
) -> None:
    pairs = [
        ("event", event),
        ("stage", stage),
        *fields.items(),
    ]
    message = " ".join(
        f"{key}={_format_log_value(value)}" for key, value in pairs
    )
    logging.getLogger(PIPELINE_LOGGER_NAME).log(
        level,
        message,
        exc_info=exc_info,
    )
