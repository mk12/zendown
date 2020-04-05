"""Zendown asset."""

from __future__ import annotations

from pathlib import Path

from zendown.tree import Node


class Asset:

    """An asset file."""

    def __init__(self, path: Path, node: Node[Asset]):
        self.path = path
        self.node = node

    def __repr__(self) -> str:
        return f"Asset(ref={self.node.ref}, path={self.path!r})"
