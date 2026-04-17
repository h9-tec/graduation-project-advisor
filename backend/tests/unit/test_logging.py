from __future__ import annotations

import io
import json
import re

from loguru import logger


def test_configure_logging_emits_json_with_context() -> None:
    from core.logging import bind_context, configure_logging

    configure_logging(level="INFO")

    sink = io.StringIO()
    sink_id = logger.add(sink, serialize=True, level="INFO")
    try:
        log = bind_context(session_id="abc", stage="retrieve", candidate_id="xyz")
        log.info("hello")
    finally:
        logger.remove(sink_id)

    raw = sink.getvalue().strip()
    # Loguru serialize=True emits one JSON per line
    payload = json.loads(raw)
    record = payload["record"]
    assert record["message"] == "hello"
    extra = record["extra"]
    assert extra["session_id"] == "abc"
    assert extra["stage"] == "retrieve"
    assert extra["candidate_id"] == "xyz"


def test_configure_logging_respects_level() -> None:
    from core.logging import configure_logging

    configure_logging(level="ERROR")

    sink = io.StringIO()
    sink_id = logger.add(sink, serialize=True, level="ERROR")
    try:
        logger.info("quiet")
        logger.error("loud")
    finally:
        logger.remove(sink_id)

    output = sink.getvalue()
    assert "quiet" not in output
    # "loud" may be escaped/wrapped in JSON; check via regex
    assert re.search(r'"message":\s*"loud"', output)
