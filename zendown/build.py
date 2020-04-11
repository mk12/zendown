"""Build targets for projects."""

import logging
import os.path
import webbrowser
from abc import ABC, abstractmethod
from importlib import resources
from pathlib import Path
from shutil import rmtree
from typing import Iterable, List, NamedTuple, Optional, Set, TextIO, Type

from jinja2 import Environment, PackageLoader, select_autoescape

from zendown import templates
from zendown.article import Article, Index, Interlink
from zendown.files import FileSystem
from zendown.project import Project
from zendown.resource import Asset
from zendown.tree import Node, Ref
from zendown.zfm import Context, RenderOptions, ZFMRenderer


class Options(NamedTuple):

    """Options for building."""


class Builder(ABC):

    """Abstract base class for all builders."""

    name: str
    supports_watch: bool

    def __init__(self, project: Project, options: Options):
        self.project = project
        self.options = options
        out_dir = project.fs.join(Path("out") / self.name)
        self.fs = FileSystem(out_dir)

    def clean(self):
        """Delete the contents of the output directory."""
        rmtree(self.fs.root)

    def context(self, article: Article) -> Context:
        """Return a Context object for macros in an article."""
        return Context(self, self.project, article)

    def resolve_link(self, ctx: Context, link: Interlink) -> str:
        """Resolve an article to a URL."""
        url = self._resolve_link(ctx, link)
        logging.debug("resolved link %s to %s", link, url)
        return url

    def resolve_asset(self, ctx: Context, asset: Asset) -> str:
        """Resolve an asset to a URL."""
        url = self._resolve_asset(ctx, asset)
        logging.debug("resolved asset %s to %s", asset, url)
        return url

    def build(self, articles: Iterable[Article], open_output: bool = False):
        """Build the given articles.

        If open_output is True, automatically opens the result in the
        appropriate application (e.g. web browser).
        """
        logging.info("building target %s", self.name)
        self.fs.root.mkdir(parents=True, exist_ok=True)
        article_list = list(articles)
        self._build(article_list)
        if open_output:
            self._open(article_list[0] if len(article_list) == 1 else None)

    @abstractmethod
    def _resolve_link(self, ctx: Context, link: Interlink) -> str:
        ...

    @abstractmethod
    def _resolve_asset(self, ctx: Context, asset: Asset) -> str:
        ...

    @abstractmethod
    def _build(self, articles: List[Article]):
        ...

    @abstractmethod
    def _open(self, article: Optional[Article]):
        ...


class Html(Builder):

    """Builds HTML web pages for direct browsing (no server needed)."""

    name = "html"
    supports_watch = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = Environment(
            loader=PackageLoader("zendown", "templates"),
            autoescape=select_autoescape(["html"]),
        )
        self.css = resources.open_text(templates, "style.css").read()
        self.index_template = self.env.get_template("index.html.jinja")
        self.article_template = self.env.get_template("article.html.jinja")
        assets = self.fs.join("assets")
        if not assets.exists():
            assets.symlink_to(self.project.fs.join("assets"), target_is_directory=True)

    def article_path(self, article: Article) -> Path:
        return self.fs.join(article.node.ref.path.with_suffix(".html"))

    def index_path(self, ref: Ref[Article]) -> Path:
        return self.fs.join(ref.path / "index.html")

    def _resolve_link(self, ctx: Context, link: Interlink) -> str:
        source = self.article_path(ctx.article).parent
        dest = self.article_path(link.article)
        rel = os.path.relpath(dest, source)
        if rel == ".":
            return "#"
        if link.section:
            return f"{rel}#{link.section.node.label}"
        return rel

    def _resolve_asset(self, ctx: Context, asset: Asset) -> str:
        path = asset.path
        if not self.project.fs.join(path).exists():
            logging.error("%s: asset %s does not exist", ctx.article.path, path)
        return self.relative_base(ctx.article.node, -1) + str(path)

    def _build(self, articles: List[Article]):
        with open(self.fs.join("style.css"), "w") as f:
            f.write(self.css)
        parents: List[Node] = []
        for article in articles:
            if article.node.parent is not None:
                parents.append(article.node.parent)
            if article.is_index():
                continue
            article.ensure_resolved(self.project)
            path = self.article_path(article)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                self.write_article(article, f)
        done: Set[Node] = set()
        while parents:
            node = parents.pop()
            if node in done:
                continue
            done.add(node)
            if node.parent:
                parents.append(node.parent)
            path = self.index_path(node.ref)
            with open(path, "w") as f:
                self.write_index(Index(node), f)

    def write_article(self, article: Article, out: TextIO):
        article.ensure_resolved(self.project)
        ctx = self.context(article)
        with ZFMRenderer(ctx, RenderOptions(shift_headings_by=1)) as r:
            body = article.render(r)
        assert article.cfg is not None
        vals = {
            "base": self.relative_base(article.node, -1),
            "title": article.cfg["title"],
            "body": body,
        }
        out.write(self.article_template.render(**vals))

    def write_index(self, index: Index, out: TextIO):
        root = index.node.is_root()
        body = None
        article = index.article
        if article:
            ctx = self.context(article)
            article.ensure_loaded()
            if not article.cfg_only:
                article.ensure_resolved(self.project)
                with ZFMRenderer(ctx, RenderOptions(shift_headings_by=1)) as r:
                    body = article.render(r)
        sections = (Index(n) for n in index.node.children.values() if n.children)
        articles = (
            n.item
            for n in index.node.children.values()
            if n.item and not n.item.is_index()
        )
        vals = {
            "base": self.relative_base(index.node),
            "root": root,
            "title": index.title,
            "body": body,
            "sections": [(s.node.label, s.title) for s in sections],
            "articles": [(a.node.label, a.title) for a in articles],
        }
        out.write(self.index_template.render(**vals))

    @staticmethod
    def relative_base(node: Node, adjust: int = 0) -> str:
        return "../" * (len(node.ref.parts) + adjust)

    def _open(self, article: Optional[Article]):
        if article:
            path = self.article_path(article)
        else:
            path = self.index_path(self.project.articles.root.ref)
        webbrowser.open(path.absolute().as_uri())


class Hubspot(Builder):

    name = "hubspot"
    supports_watch = False

    def _resolve_link(self, ctx: Context, link: Interlink) -> str:
        return ""

    def _resolve_asset(self, ctx: Context, asset: Asset) -> str:
        return ""

    def _build(self, articles: List[Article]):
        print("TODO")

    def _open(self, article: Optional[Article]):
        print("TODO")


_builder_list: List[Type[Builder]] = [Html, Hubspot]

builders = {b.name: b for b in _builder_list}
