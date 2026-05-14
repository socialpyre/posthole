"""Terminal output: ANSI colors + the structlog console renderer."""

from __future__ import annotations

import re
from typing import Any

LEVEL_COLORS = {
    "debug": "\x1b[36m",  # cyan
    "info": "\x1b[32m",  # green
    "warning": "\x1b[33m",  # yellow
    "error": "\x1b[31m",  # red
    "critical": "\x1b[31;1m",  # bold red
}
RESET = "\x1b[0m"

# C0 + DEL + C1 control characters. Stripped from rendered event text so a
# user-derived log value can't inject terminal escape sequences (fake log
# lines via CR, hyperlink injection, screen clears, etc.) into the dev
# console. JSON mode renders via JSONRenderer which already escapes these.
CTRL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def console_renderer(_logger: Any, _method_name: str, event_dict: dict[str, Any]) -> str:
    """Render a structlog event to match fastapi's renderer."""
    level = str(event_dict.pop("level", "info")).lower()
    event = scrub_ctrl(str(event_dict.pop("event", "")))

    color = LEVEL_COLORS.get(level, "")
    label = level.upper()

    # Pad on the uncolored label length — ANSI codes don't take visible width.
    padding = " " * max(0, 10 - len(label))
    colored = f"{color}{label}{RESET}" if color else label

    parts = [padding, colored, "   ", event]
    for k, v in event_dict.items():
        parts.append(f"  {k}={format_value(v)}")
    return "".join(parts)


def format_value(v: Any) -> str:
    """Render a structured field value for the ``key=value`` tail.

    Always uses ``repr()`` — that escapes control characters (including ANSI
    ``\\x1b`` sequences) and adds unambiguous quotes around strings containing
    ``=``, spaces, etc. Non-strings render as their literal Python form.
    """
    return repr(v)


def scrub_ctrl(s: str) -> str:
    """Replace ASCII/Unicode control chars with their ``\\xNN`` escape."""
    return CTRL_CHARS.sub(lambda m: f"\\x{ord(m.group()):02x}", s)
