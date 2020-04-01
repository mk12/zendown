"""Zendown article."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from mistletoe.block_token import BlockToken, Document, Heading
from slugify import slugify

from zendown.config import Config
from zendown.tokens import collect_text
from zendown.tree import Label, Node
from zendown.zfm import Context, ZFMRenderer, postprocess_heading


class ArticleConfig(Config):

    """Article configuration header."""

    required = {
        "title": "Untitled Article",
    }

    optional = {
        "slug": None,  # default set in Article.load
    }


class Section:

    """A section within an article body.

    A section is defined by a heading. It can be any level (H1 to H6). The
    section stores the blocks up until the next heading of equal or lower level
    (which are not children of the heading in the mistletoe tokenization).
    """

    def __init__(self, node: Node["Section"], heading: Heading):
        self.node = node
        self.heading = heading
        self.blocks: List[BlockToken] = []


# Sections form a tree, but we refer to them by Label rather than Ref because
# they must have unique labels (since they are used for the HTML id attribute).
Anchor = Label[Section]


class ParseError(Exception):
    """An error that occurs while parsing an article."""


class Article:

    """An article written in ZFM with a YAML configuration header.

    An article can be in one of three states:

    1. Initialized: Only self.path and self.node are set.
    2. Loaded: The file at self.path has been read, and split into the parsed
       configuration (self.cfg) and the raw body (self.raw).
    3. Parsed: The body has been tokenized (self._doc) and section tree has been
       created (self._tree, self._anchors).

    Loading must be done explicitly by calling load() or ensure_loaded(). Once
    loaded, the other properties (self.doc, self.tree, self.anchors) will
    automatically perform parsing if it has not been done yet.

    Rendering to HTML can be considered a final step after parsing, but the
    rendered results are not stored in the object.
    """

    def __init__(self, path: Path, node: Node["Article"]):
        """Create a new article at the given filesystem path and tree node."""
        self.path = path
        self.node = node
        self.cfg: Optional[Mapping[str, Any]] = None
        self.raw: Optional[str] = None
        self._doc: Optional[Document] = None
        self._tree: Optional[Node[Section]] = None
        self._anchors: Optional[Dict[Anchor, Section]] = None

    def __repr__(self) -> str:
        return f"Article(ref={self.node.ref!r}, path={self.path!r})"

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
        logging.info("loading article %r from %s", self.node.ref, self.path)
        with open(self.path) as f:
            head = ""
            for line in f:
                if line.rstrip() == "---":
                    break
                head += line
            body = f.read()
        default_slug = slugify(self.path.with_suffix("").name)
        self.cfg = ArticleConfig.loads(self.path, head)
        self.cfg.validate(slug=default_slug)
        logging.debug("article %r config: %r", self.node.ref, self.cfg)
        self.raw = body
        self._doc = None
        self._tree = None
        self._anchors = None

    def is_parsed(self) -> bool:
        """Return true if the article has been loaded and parsed."""
        return bool(self._doc)

    def parse(self):
        """Parse the loaded ZFM body.

        Unlike loading, this does not need to be called manually. It will happen
        on demand when properties are accessed.
        """
        assert self.is_loaded()
        logging.info("parsing article %r", self.node.ref)
        self._doc = Document(self.raw)
        self._tree = Node.root()
        self._anchors = {}
        parent = self._tree
        blocks = []
        prev = None
        for token in self.doc.children:
            if not isinstance(token, Heading):
                blocks.append(token)
                continue
            if prev:
                prev.item.blocks = blocks
            blocks = []
            postprocess_heading(token)
            if token.identifier:
                original_id = token.identifier
                if Label(original_id) in self.anchors:
                    logging.error("%s: duplicate heading ID %r", self.path, original_id)
            else:
                original_id = slugify(collect_text(token))
            i = 1
            unique_id = original_id
            while Label(unique_id) in self._anchors:
                unique_id = f"{original_id}-{i}"
                i += 1
            # Set token.identifier since it will be rendered to the HTML id.
            token.identifier = unique_id
            label = Label(unique_id)
            node = Node(label)
            section = Section(node, token)
            node.set_item(section)
            self._anchors[label] = section
            if prev and token.level > prev.item.heading.level:
                parent = prev
            else:
                while parent.item and token.level <= parent.item.heading.level:
                    parent = parent.parent
            parent.add_child(node)
            prev = node
        if prev:
            prev.item.blocks = blocks

        def extend_blocks(node: Node[Section]) -> List[BlockToken]:
            assert node.item
            for child in node.children.values():
                node.item.blocks.extend(extend_blocks(child))
            return [node.item.heading] + node.item.blocks

        for node in self._tree.children.values():
            extend_blocks(node)
        self._tree.set_refs_recursively()

    @property
    def doc(self) -> Document:
        """Return the tokenized Markdown document."""
        if not self.is_parsed():
            self.parse()
        return self._doc

    @property
    def tree(self) -> Node[Section]:
        """Return the tree of sections in the article."""
        if not self.is_parsed():
            self.parse()
        assert self._tree is not None
        return self._tree

    @property
    def anchors(self) -> Dict[Label[Section], Section]:
        """Return a mapping from anchors to sections (all levels)."""
        if not self.is_parsed():
            self.parse()
        assert self._anchors is not None
        return self._anchors

    def render_html(self, ctx: Context):
        """Render from ZFM Markdown to HTML."""
        with ZFMRenderer(ctx) as renderer:
            return renderer.render(self.doc)
