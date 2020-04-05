"""Zendown article."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Container, Dict, List, Optional, cast

from mistletoe.block_token import Document, Heading
from mistletoe.span_token import Image, Link
from slugify import slugify

from zendown.asset import Asset
from zendown.config import Config
from zendown.include import Include
from zendown.section import Anchor, Section, parse_sections
from zendown.tokens import Token, collect_text, walk
from zendown.tree import Label, Node, Ref, Tree
from zendown.zfm import Context, ZFMRenderer, parse_document

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from zendown.project import Project


class Interlink:

    """A link to an article, optionally specifying a section.

    Interlink is short for "inter-article link".
    """

    def __init__(self, article: Article, section: Optional[Section]):
        self.article = article
        self.section = section

    def __repr__(self) -> str:
        return f"Interlink(article={self.article!r}, section={self.section!r})"

    def __str__(self) -> str:
        if self.section:
            return f"{self.article.node.ref}#{self.section.node.label}"
        return str(self.article.node.ref)


class ArticleConfig(Config):

    """Article configuration header."""

    required = {
        "title": "Untitled Article",
    }

    optional = {
        "slug": None,  # default set in Article.load
    }


class Article:

    """An article written in ZFM with a YAML configuration header.

    An article can be in one of four states:

    1. Initialized: Only self.path and self.node are set.
    2. Loaded: The file at self.path has been read, and split into the parsed
       configuration (self.cfg) and the raw body (self.raw).
    3. Parsed: The body has been tokenized (self.doc) and section tree has been
       created (self.sections, self.anchors).
    4. Resolved: Externa; resources have been resolved within the project
       (self.links, self.assets, self.includes).

    Loading and resolving must be done explicitly. After loading, the properties
    self.doc, self.sections, and self.anchors will automatically perform parsing
    if it has not been done yet.

    Rendering to HTML can be considered a final step after resolving, but the
    rendered results are not stored in the object.
    """

    def __init__(self, path: Path, node: Node[Article]):
        """Create a new article at the given filesystem path and tree node."""
        self.path = path
        self.node = node
        self.cfg: Optional[ArticleConfig] = None
        self.raw: Optional[str] = None
        self._doc: Optional[Document] = None
        self._sections: Optional[Tree[Section]] = None
        self._anchors: Optional[Dict[Anchor, Section]] = None
        self._links: Optional[List[Interlink]] = None
        self._assets: Optional[List[Asset]] = None
        self._includes: Optional[List[Include]] = None

    def __repr__(self) -> str:
        return f"Article(ref={self.node.ref!r}, path={self.path!r})"

    def is_loaded(self) -> bool:
        """Return true if the article has been loaded."""
        return self.raw is not None

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
        self._sections = None
        self._anchors = None

    def is_parsed(self) -> bool:
        """Return true if the article has been loaded and parsed."""
        return self._doc is not None

    def parse(self):
        """Parse the loaded ZFM body.

        Unlike loading, this does not need to be called manually. It will happen
        on demand when properties are accessed.
        """
        assert self.is_loaded()
        logging.info("parsing article %r", self.node.ref)
        assert self.raw is not None
        self._doc = parse_document(self.raw)
        self._sections = parse_sections(self._doc.children, self.gen_heading_label)
        # Cast since we know there will be no collisions.
        self._anchors = self._sections.by_unique_label

    def gen_heading_label(self, heading: Heading, used: Container[Anchor]) -> Anchor:
        """Choose a label for the heading that is not already used."""
        if heading.identifier:
            original_id = heading.identifier
            if Label(original_id) in used:
                logging.error("%s: duplicate heading ID %r", self.path, original_id)
        else:
            original_id = slugify(collect_text(heading))
        i = 1
        unique_id = original_id
        while Label(unique_id) in used:
            unique_id = f"{original_id}-{i}"
            i += 1
        # Set heading.identifier since it will be rendered as the HTML id.
        heading.identifier = unique_id
        return Label(unique_id)

    @property
    def doc(self) -> Document:
        """Return the tokenized Markdown document."""
        if not self.is_parsed():
            self.parse()
        return self._doc

    @property
    def sections(self) -> Tree[Section]:
        """Return the tree of sections in the article."""
        if not self.is_parsed():
            self.parse()
        assert self._sections is not None
        return self._sections

    @property
    def anchors(self) -> Dict[Anchor, Section]:
        """Return a mapping from anchors to sections (all levels)."""
        if not self.is_parsed():
            self.parse()
        assert self._anchors is not None
        return self._anchors

    def is_resolved(self) -> bool:
        """Return true if the article has been loaded, parsed, and resolved."""
        return self._links is not None

    def ensure_resolved(self, project: Project):
        """Resolve the article if it is not already resolved."""
        if not self.is_resolved():
            self.resolve(project)

    def resolve(self, project: Project):
        """Resolve the parsed article within the project."""
        assert self.is_parsed()
        logging.info("resolving article %r", self.node.ref)
        self._links = []
        self._assets = []
        self._includes = []

        def visit(token: Token):
            pass
            # if isinstance(token, Link):
            #     if not token.target or "." in token.target:
            #         return
            #     path, anchor = token.target, ""
            #     if "#" in path:
            #         path, anchor = path.split("#", 1)
            #     article: Optional[Article] = None
            #     if path == "":
            #         article = self
            #     elif path.startswith("/"):
            #         ref: Ref[Article] = Ref.parse(path)
            #         article = project.articles_by_ref.get(ref)
            #     elif "/" not in path:
            #         label: Label[Article] = Label(path)
            #         maybe_article = self.ctx.project.articles_by_label.get(label)
            #         if maybe_article is COLLISION:
            #             return self.error(f"ambiguous article name {path!r}")
            #         article = cast(Optional["Article"], maybe_article)
            #     # if not article:
            #     # link = Interlink(article, section)
            # elif isinstance(token, Image):
            #     pass

        walk(self._doc, visit)

    @property
    def links(self) -> List[Interlink]:
        """Return the article's links."""
        assert self.is_resolved()
        assert self._links is not None
        return self._links

    @property
    def assets(self) -> List[Asset]:
        """Return the article's assets."""
        assert self.is_resolved()
        assert self._assets is not None
        return self._assets

    @property
    def includes(self) -> List[Include]:
        """Return the article's includes."""
        assert self.is_resolved()
        assert self._includes is not None
        return self._includes

    def render_html(self, ctx: Context):
        """Render from ZFM Markdown to HTML."""
        with ZFMRenderer(ctx) as renderer:
            return renderer.render(self.doc)
