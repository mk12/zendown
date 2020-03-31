"""Miscellaneous utilities."""

import re
import sys


def fatal_error(message: str):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def smartify(text: str) -> str:
    """Augment text with smart typography.

    This replaces dumb quotes with curly quotes, "..." with ellipses, and "--"
    with em dashes.
    """
    text = re.sub(r"([a-zA-Z0-9.,?!;:\'\"])\"", r"\1”", text)
    text = text.replace(r'"', r"“")
    text = re.sub(r"([a-zA-Z0-9.,?!;:\'\"])'", r"\1’", text)
    text = text.replace(r"'", r"‘")
    text = text.replace(r"...", r"…")
    text = text.replace(r"--", r"—")
    return text
