"""Generic resource."""

from __future__ import annotations

import logging
from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING, Optional, TypeVar

from mistletoe.block_token import Document

from zendown.tree import Node
from zendown.zfm import parse_document

T = TypeVar("T", bound="Resource")

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from zendown.project import Project


class Resource(ABC):

    """A file-backed resource.

    This class serves to consolidate logic common to all Zendown resources.
    Resources correspond to a file on disk, and are stored in trees. They can
    optionally have loading, parsing, and resolving stages. For example, to
    support a loading stage, a subclass should override is_loaded and _load.

    The ensure_* methods automatically perform earlier stages if necessary. For
    example, ensure_resolved will load, parse, and resolve if the resource has
    not been loaded yet.
    """

    def __init__(self: T, path: Path, node: Node[T]):
        self.path = path
        self.node = node

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"{name}(ref={self.node.ref}, path={self.path!r})"

    def is_loaded(self) -> bool:
        """Return true if the resource has been loaded."""
        return True

    def ensure_loaded(self):
        """Load the resource if it is not already loaded."""
        if not self.is_loaded():
            self.load()

    def load(self):
        """Load the resource from disk."""
        if self.is_loaded():
            return
        name = self.__class__.__name__.lower()
        logging.info("loading %s %s from %s", name, self.node.ref, self.path)
        self._load()

    def _load(self):
        ...

    def is_parsed(self) -> bool:
        """Return true if the resource has been parsed."""
        return True

    def ensure_parsed(self):
        """Parse the loaded resource if it is not already parsed."""
        if not self.is_parsed():
            self.ensure_loaded()
            self.parse()

    def parse(self):
        """Parse the loaded resource."""
        assert self.is_loaded()
        if self.is_parsed():
            return
        name = self.__class__.__name__.lower()
        logging.info("parsing %s %s", name, self.node.ref)
        self._parse()

    def _parse(self):
        ...

    def is_resolved(self) -> bool:
        """Return true if the resource has been resolved."""
        return True

    def ensure_resolved(self, project: Project):
        """Resolve the parsed resource if it is not already resolved."""
        if not self.is_resolved():
            self.ensure_parsed()
            self.resolve(project)

    def resolve(self, project: Project):
        """Resolve the parsed resource."""
        assert self.is_parsed()
        if self.is_resolved():
            return
        name = self.__class__.__name__.lower()
        logging.info("resolving %s %s in project %s", name, self.node.ref, project.name)
        self._resolve(project)

    def _resolve(self, project: Project):
        ...


class Asset(Resource):

    """An asset file.

    In the future, this might require loading for manipulating images during the
    build (e.g., adding borders).
    """


class Include(Resource):

    """A file to be included in articles."""

    def __init__(self, path: Path, node: Node[Include]):
        super().__init__(path, node)
        self.raw: Optional[str] = None
        self._doc: Optional[Document] = None

    def is_loaded(self) -> bool:
        return self.raw is not None

    def _load(self):
        with open(self.path) as f:
            self.raw = f.read()

    def is_parsed(self) -> bool:
        return self._doc is not None

    def _parse(self):
        assert self.raw is not None
        self._doc = parse_document(self.raw)

    @property
    def doc(self) -> Document:
        """Return the tokenized Markdown document."""
        self.ensure_parsed()
        assert self._doc is not None
        return self._doc
