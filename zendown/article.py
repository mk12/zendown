"""Zendown article."""

from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from mistletoe import Document
from mistletoe.ast_renderer import ASTRenderer

from zendown.config import ArticleConfig
from zendown.tree import Node
from zendown.zfm import Context, ZFMRenderer


class Article:

    """An article written in ZFM with a YAML configuration header."""

    def __init__(self, path: Path, node: Node["Article"]):
        """Create a new article at the given filesystem path and tree node."""
        self.path = path
        self.node = node
        self.cfg: Optional[Mapping[str, Any]] = None
        self.raw: Optional[str] = None
        self._doc: Optional[Document] = None
        self._ast: Optional[Dict] = None

    def is_loaded(self) -> bool:
        """Return true if the article has been loaded."""
        return bool(self.raw)

    def ensure_loaded(self):
        """Load the article if it is not already loaded."""
        if not self.is_loaded():
            self.load()

    def load(self):
        """Load the article from disk.

        This sets self.cfg (parsed configuration) and self.raw (raw, unparsed
        body of the article).
        """
        with open(self.path) as f:
            head = ""
            for line in f:
                if line.rstrip() == "---":
                    break
                head += line
            body = f.read()
        self.cfg = ArticleConfig.loads(self.path, head)
        self.raw = body
        self._doc = None
        self._ast = None

    @property
    def doc(self) -> Document:
        """Return the tokenized Markdown document."""
        assert self.is_loaded()
        if self._doc is None:
            self._doc = Document(self.raw)
        return self._doc

    @property
    def ast(self) -> Dict:
        """Return the Markdown abstract syntax tree."""
        assert self.is_loaded()
        if self._ast is None:
            with ASTRenderer() as renderer:
                self._ast = renderer.render(self.doc)
        return self._ast

    def render_html(self, ctx: Context):
        """Render from ZFM Markdown to HTML."""
        with ZFMRenderer(ctx) as renderer:
            return renderer.render(self.doc)
