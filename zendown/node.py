"""Graph representation of Zendown objects."""

from pathlib import Path
from typing import Iterable, Optional


from zendown.config import Config


class Node:

    """A node in the Zendown project."""

    def __init__(self, path: Path, ref: str):
        self.path = path
        self.ref = ref
