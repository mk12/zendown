"""Zendown article."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Container,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    cast,
)

from mistletoe.block_token import BlockToken, Document, Heading
from mistletoe.span_token import Image, Link
from slugify import slugify

from zendown.config import Config
from zendown.resource import Asset, Include, Resource
from zendown.tokens import Token, collect_text, walk
from zendown.tree import COLLISION, Label, Node, Ref, Tree
from zendown.zfm import BlockMacro, ZFMRenderer, parse_document

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from zendown.project import Project


class Section:

    """A section within an article body.

    A section comprises a heading and a list of blocks. The heading can be any
    level (H1 to H6). The section stores blocks up until the next heading of
    equal or lower level (i.e. same or bigger font).

    This class is useful for manipulating article content, since the mistletoe
    tokenization is flat with respect to headings.
    """

    def __init__(self, heading: Heading, node: Node[Section]):
        self.heading = heading
        self.node = node
        self.blocks: List[BlockToken] = []


# Sections form a tree, but we refer to them by Label rather than Ref because
# they must have unique labels (since they are used for the HTML id attribute).
Anchor = Label[Section]


# A function that generates a label for a heading, given the set of used labels.
GenLabelFn = Callable[[Heading, Container[Anchor]], Anchor]


def parse_sections(
    tokens: Sequence[BlockToken], gen_label: Optional[GenLabelFn] = None
) -> Tree[Section]:
    """Parse tokens into a tree of sections.

    If gen_label is provided, it will be used to generate labels in the tree.
    Otherwise, unspecified integers will be used.
    """
    if not gen_label:
        gen_label = lambda heading, used: Label(str(id(heading)))
    tree: Tree[Section] = Tree()
    parent = tree.root
    blocks = []
    node = None
    used: Set[Anchor] = set()
    for token in tokens:
        if not isinstance(token, Heading):
            blocks.append(token)
            continue
        if node:
            node.item.blocks = blocks
        blocks = []
        label = gen_label(token, used)
        used.add(label)
        if node and token.level > node.item.heading.level:
            parent = node
        else:
            while parent.item and token.level <= parent.item.heading.level:
                assert parent.parent
                parent = parent.parent
        node = parent.add_child(label)
        tree.register(node, Section(token, node))
    if node:
        assert node.item
        node.item.blocks = blocks

    # At this point, the Section objects only store the blocks up to the
    # next heading. Extend them to cover all the blocks in their subtree.
    def extend_blocks(node: Node[Section]) -> List[BlockToken]:
        assert node.item
        for child in node.children.values():
            node.item.blocks.extend(extend_blocks(child))
        return [node.item.heading] + node.item.blocks

    for node in tree.root.children.values():
        extend_blocks(node)
    return tree


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
        "subtitle": None,
        "tags": [],
        "order": [],  # used in index articles to specify order of children
    }


class ResolveError(Exception):
    """An error that occurs during article resolution."""


class Article(Resource):

    """An article written in ZFM with a YAML configuration header.

    Normal articles should have a .md extension and a "---" line to separate
    configuration from body. Config-only articles should have an .yml extension
    and consist only of YAML.

    An article can be in one of four states:

    1. Initialized: Only self.path and self.node are set.
    2. Loaded: The file at self.path has been read, and split into the parsed
       configuration (self.cfg) and the raw body (self.raw).
    3. Parsed: The body has been tokenized (self.doc) and section tree has been
       created (self.sections, self.anchors).
    4. Resolved: Externa; resources have been resolved within the project
       (self.links, self.assets, self.includes).

    Rendering to HTML can be considered a final step after resolving, but the
    rendered results are not stored in the object.
    """

    node: Node[Article]

    def __init__(self, path: Path, node: Node[Article]):
        super().__init__(path, node)
        self.cfg_only = path.suffix == ".yml"
        self.cfg: Optional[ArticleConfig] = None
        self.raw: Optional[str] = None
        self._doc: Optional[Document] = None
        self._sections: Optional[Tree[Section]] = None
        self._links: Optional[List[Interlink]] = None
        self._assets: Optional[List[Asset]] = None
        self._includes: Optional[List[Include]] = None

    def is_index(self) -> bool:
        """Return true if this is an index article.

        An index article is a special article in a section that defines content
        for the index page. It can be a full article or a config-only file.
        """
        return self.node.label == Label("index")

    def is_loaded(self) -> bool:
        return self.raw is not None

    def _unload(self):
        self.raw = None
        self.cfg = None

    def _load(self):
        with self.open_file() as f:
            head = ""
            for line in f:
                if line.rstrip() == "---":
                    if self.cfg_only:
                        logging.error("article %s should be .md, not .yml", self.path)
                    break
                head += line
            else:
                if not self.cfg_only:
                    logging.error("article %s should be .yml, not .md", self.path)
            body = f.read()
        if self.is_index():
            default_slug = slugify(self.path.parent.name)
        else:
            default_slug = slugify(self.path.with_suffix("").name)
        self.cfg = ArticleConfig.loads(self.path, head)
        self.cfg.validate(slug=default_slug)
        logging.debug("article %s config: %r", self.node.ref, self.cfg)
        self.raw = body

    @property
    def title(self) -> str:
        """Return the title of the article."""
        self.ensure_loaded()
        assert self.cfg is not None
        return self.cfg["title"]

    @property
    def slug(self) -> str:
        """Return the slug of the article."""
        self.ensure_loaded()
        assert self.cfg is not None
        return self.cfg["slug"]

    def is_parsed(self) -> bool:
        return self._doc is not None

    def _unparse(self):
        self._doc = None
        self._sections = None

    def _parse(self):
        assert self.raw is not None
        self._doc = parse_document(self.raw)
        self._sections = parse_sections(self._doc.children, self.gen_heading_label)

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
        self.ensure_parsed()
        assert self._doc is not None
        return self._doc

    @property
    def sections(self) -> Tree[Section]:
        """Return the tree of sections in the article."""
        self.ensure_parsed()
        assert self._sections is not None
        return self._sections

    @property
    def anchors(self) -> Dict[Anchor, Section]:
        """Return a mapping from anchors to sections (all levels)."""
        return self.sections.by_unique_label

    def is_resolved(self) -> bool:
        return self._links is not None

    def _unresolve(self):
        self._links = None
        self._assets = None
        self._includes = None

    def _resolve(self, project: Project):
        self._links = []
        self._assets = []
        self._includes = []

        def visit(token: Token):
            try:
                if isinstance(token, Link):
                    link = self.resolve_link(token.target, project)
                    if link:
                        token.zfm_interlink = link
                        assert self._links is not None
                        self._links.append(link)
                elif isinstance(token, Image):
                    # TODO: Refactor this to something nicer.
                    match = re.fullmatch(
                        r"^([^=]+)=([0-9]+|\?)x([0-9]+|\?)$", token.src
                    )
                    if match:
                        token.src = match.group(1)
                        width, height = match.group(2), match.group(3)
                        width = None if width == "?" else int(width)
                        height = None if height == "?" else int(height)
                        token.zfm_size = width, height
                    asset = self.resolve_asset(token.src, project)
                    if asset:
                        token.zfm_asset = asset
                        assert self._assets is not None
                        self._assets.append(asset)
                elif isinstance(token, BlockMacro) and token.name == "include":
                    include = self.resolve_include(token.arg, project)
                    if include:
                        token.zfm_include = include
                        assert self._includes is not None
                        self._includes.append(include)
            except ResolveError as ex:
                message = str(ex)
                logging.error("%s: %s", self.path, message)
                token.zfm_error = message

        walk(self._doc, visit)

    def resolve_link(self, url: str, project: Project) -> Optional[Interlink]:
        """Resolve an article link in the project."""
        if not url or "." in url:
            return None
        path, anchor = url, ""
        if "#" in path:
            path, anchor = path.split("#", 1)
        article: Optional[Article] = None
        if path == "":
            article = self
        elif path.startswith("/"):
            ref: Ref[Article] = Ref.parse(path)
            article = project.articles.by_ref.get(ref)
        elif "/" not in path:
            label: Label[Article] = Label(path)
            maybe_article = project.articles.by_label.get(label)
            if maybe_article is COLLISION:
                raise ResolveError(f"ambiguous article reference {path!r}")
            article = cast(Optional["Article"], maybe_article)
        if not article:
            raise ResolveError(f"invalid article reference {path!r}")
        section = None
        if anchor:
            section = article.anchors.get(Label(anchor))
            if not section:
                raise ResolveError(
                    f"invalid anchor #{anchor} for article {article.node.ref}"
                )
        return Interlink(article, section)

    def resolve_asset(self, url: str, project: Project) -> Optional[Asset]:
        """Resolve an asset in the project."""
        if url.startswith("http://") or url.startswith("https://"):
            return None
        ref: Ref[Asset] = Ref.parse(url, leading_slash=False)
        asset = project.get_asset(ref)
        if not asset:
            raise ResolveError(f"invalid asset reference {url!r}")
        return asset

    def resolve_include(self, path: str, project: Project) -> Optional[Include]:
        """Resolve an include in the project."""
        ref: Ref[Include] = Ref.parse(path, leading_slash=False)
        include = project.get_include(ref)
        if not include:
            raise ResolveError(f"invalid include reference {path!r}")
        return include

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

    def render(self, renderer: ZFMRenderer):
        """Render from ZFM Markdown to HTML."""
        assert self.is_resolved()
        return renderer.render(self.doc)


class Index:

    """Class for dealing with /index articles.

    An index consists of an internal node of the article tree and (optionally,
    if present) the /index article underneath it. Internal nodes do not directly
    have article items because this does not map onto the filesystem well.
    """

    def __init__(self, node: Node[Article]):
        assert node.item is None
        self.node = node
        self.article = None
        if Label("index") in node.children:
            self.article = node.children[Label("index")].item
            assert self.article is not None

    @property
    def title(self) -> str:
        """Return the title of the index."""
        if self.article:
            return self.article.title
        return str(self.node.label)

    @property
    def slug(self) -> str:
        """Return the slug for the index."""
        if self.article:
            return self.article.slug
        return slugify(str(self.node.label))
