"""Zendown include files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from mistletoe.block_token import BlockToken

from zendown.tree import Node


class Include:

    """An file to be included in articles."""

    def __init__(self, path: Path, node: Node[Include]):
        self.path = path
        self.node = node
        self.raw: Optional[str] = None
        self._tokens: Optional[List[BlockToken]] = None

    def __repr__(self) -> str:
        return f"Include(ref={self.node.ref}, path={self.path!r})"

    def is_loaded(self) -> bool:
        """Return true if the include file has been loaded."""
        return self.raw is not None

    def ensure_loaded(self):
        """Load the include file if it is not already loaded."""
        if not self.is_loaded():
            self.load()

    def load(self):
        """Load the include file from disk."""
        logging.info("loading include file %s", self.path)
        with open(self.path) as f:
            self.raw = f.read()

    def is_parsed(self) -> bool:
        """Return true if the include file has been loaded and parsed."""
        return self._tokens is not None

    def parse(self):
        """Parse the loaded include file."""
        assert self.is_loaded()
        logging.info("parsing include %s", self.path)
        self._tokens = []
        # TODO!!

    @property
    def tokens(self) -> List[BlockToken]:
        """Return the tokenized include file."""
        if not self.is_parsed():
            self.parse()
        assert self._tokens
        return self._tokens
