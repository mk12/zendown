"""Generic resource."""

from __future__ import annotations

import logging
from abc import ABC
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from mistletoe.block_token import Document

from zendown.tree import Node
from zendown.zfm import parse_document

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from zendown.project import Project


class Resource(ABC):

    """A file-backed resource.

    This class serves to consolidate logic common to all Zendown resources.
    Resources correspond to a file on disk, and are stored in trees. They can
    optionally have loading, parsing, and resolving stages. For example, to
    support a loading stage, a subclass should override the is_loaded and _load,
    and _unload methods.

    The ensure_* methods automatically perform earlier stages if necessary. For
    example, ensure_resolved will load, parse, and resolve if the resource has
    not been loaded yet.
    """

    # Tried using self: T` and node: Node[T] with TypeVar("T", bound="Resource")
    # but ran into issues. Also tried Node[Resource] but had trouble making Node
    # covariant. Decided to declare it Node and refine the type in subclasses.
    def __init__(self, path: Path, node: Node):
        self.path = path
        self.node = node

    def __repr__(self) -> str:
        return f"{self.kind()}(ref={self.node.ref}, path={self.path!r})"

    def kind(self) -> str:
        return self.__class__.__name__

    @contextmanager
    def open_file(self):
        try:
            with open(self.path) as f:
                yield f
        except FileNotFoundError:
            logging.error("%s: file disappeared", self.path)
            yield StringIO("")

    def is_loaded(self) -> bool:
        """Return true if the resource has been loaded."""
        return True

    def ensure_loaded(self):
        """Load the resource if it is not already loaded."""
        if not self.is_loaded():
            self.load()

    def load(self):
        """Load the resource from disk."""
        logging.info("loading %s %s from %s", self.kind(), self.node.ref, self.path)
        self.unload()
        self._load()

    def unload(self):
        """Reset to the unloaded state."""
        logging.debug("reset %s %s to pre-load", self.kind(), self.node.ref)
        self._unresolve()
        self._unparse()
        self._unload()

    def _load(self):
        ...

    def _unload(self):
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
        self.unparse()
        logging.info("parsing %s %s", self.kind(), self.node.ref)
        self._parse()

    def unparse(self):
        """Reset to the unparsed state."""
        logging.debug("reset %s %s to pre-parse", self.kind(), self.node.ref)
        self._unresolve()
        self._unparse()

    def _parse(self):
        ...

    def _unparse(self):
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
        logging.info(
            "resolving %s %s in project %s", self.kind(), self.node.ref, project.name
        )
        self.unresolve()
        self._resolve(project)

    def unresolve(self):
        """Reset to the unresolved state."""
        logging.debug("reset %s %s to pre-resolve", self.kind(), self.node.ref)
        self._unresolve()

    def _resolve(self, project: Project):
        ...

    def _unresolve(self):
        ...


class Asset(Resource):

    """An asset file.

    In the future, this might require loading for manipulating images during the
    build (e.g., adding borders).
    """

    node: Node[Asset]


class Include(Resource):

    """A file to be included in articles."""

    node: Node[Include]

    def __init__(self, path: Path, node: Node[Include]):
        super().__init__(path, node)
        self.raw: Optional[str] = None
        self._doc: Optional[Document] = None

    def is_loaded(self) -> bool:
        return self.raw is not None

    def _unload(self):
        self.raw = None

    def _load(self):
        with self.open_file() as f:
            self.raw = f.read()

    def is_parsed(self) -> bool:
        return self._doc is not None

    def _unparse(self):
        self._doc = None

    def _parse(self):
        assert self.raw is not None
        self._doc = parse_document(self.raw)

    @property
    def doc(self) -> Document:
        """Return the tokenized Markdown document."""
        self.ensure_parsed()
        assert self._doc is not None
        return self._doc
