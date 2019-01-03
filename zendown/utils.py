"""Miscellaneous utilities."""

import sys


def fatal_error(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)
