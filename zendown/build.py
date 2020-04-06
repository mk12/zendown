"""Build targets for projects."""

import logging
from abc import ABC, abstractmethod
import os.path
from pathlib import Path
from typing import Iterator, List, NamedTuple, Set, TextIO, Type

from zendown.article import Article, Interlink
from zendown.files import FileSystem
from zendown.project import Project
from zendown.resource import Asset
from zendown.tree import Node, Ref
from zendown.zfm import Context


class Options(NamedTuple):

    """Options for building."""


class Builder(ABC):

    """Abstract base class for all builders."""

    name: str

    def __init__(self, project: Project, options: Options):
        self.project = project
        self.options = options
        out_dir = project.fs.join(Path("out") / self.name)
        out_dir.mkdir(parents=True, exist_ok=True)
        self.fs = FileSystem(out_dir)

    def context(self, article: Article) -> Context:
        """Return a Context object for macros in an article."""
        return Context(self, self.project, article)

    @abstractmethod
    def resolve_link(self, ctx: Context, link: Interlink) -> str:
        """Resolve an article to a URL."""

    @abstractmethod
    def resolve_asset(self, ctx: Context, asset: Asset) -> str:
        """Resolve an asset to a URL."""

    @abstractmethod
    def build(self, articles: Iterator[Article]):
        """Build the given articles."""


CSS_STYLE = """
body {
    margin: 5% auto;
    background: #f2f2f2;
    color: #444444;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 16px;
    line-height: 1.8;
    max-width: 73%;
}
a {
    border-bottom: 1px solid #444444;
    color: #444444;
    text-decoration: none;
}
a:hover {
    border-bottom: 0;
}
.note, .tip, .warning {
    background: #cff2ff;
    padding: 10px 10px 1px;
}
"""


class Html(Builder):

    """Builds HTML web pages for direct browsing (no server needed)."""

    name = "html"

    def article_path(self, article: Article) -> Path:
        return self.fs.join(Path(str(article.node.ref)[1:]).with_suffix(".html"))

    def index_path(self, ref: Ref[Article]) -> Path:
        return self.fs.join(Path(str(ref)[1:]) / "index.html")

    def resolve_link(self, ctx: Context, link: Interlink) -> str:
        source = self.article_path(ctx.article)
        dest = self.article_path(link.article)
        rel = os.path.relpath(dest, source)
        if rel == ".":
            return "#"
        return rel

    def resolve_asset(self, ctx: Context, asset: Asset) -> str:
        path = asset.path
        if not self.project.fs.join(path).exists():
            logging.error("%s: asset %s does not exist", ctx.article.path, path)
        ref = ctx.article.node.ref
        assert ref
        to_root = "../" * (1 + len(ref.parts))
        return to_root + str(path)

    def build(self, articles: Iterator[Article]):
        parents: List[Node] = []
        for article in articles:
            if article.node.parent is not None:
                parents.append(article.node.parent)
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
                self.write_index(node, f)

    def write_article(self, article: Article, out: TextIO):
        article.ensure_loaded()
        assert article.cfg is not None
        title = article.cfg["title"]
        ctx = self.context(article)
        body = article.render_html(ctx)
        print(
            f"""
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{CSS_STYLE}
</style>
</head>
<body>
<a href="index.html">Index</a>
<h1>{title}</h1>
{body}
</body>
</html>
""",
            file=out,
        )

    def write_index(self, node: Node, out: TextIO):
        root = node.is_root()
        title = self.project.name if root else str(node.ref.parts[-1]).capitalize()
        print(
            f"""
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{CSS_STYLE}
</style>
</head>
<body>
{'<a href="../index.html">Go up</a>' if not root else ''}
<h1>{title}</h1>
""",
            file=out,
        )
        if any(n.children for n in node.children.values()):
            print("<h2>Sections</h2>\n<ul>", file=out)
            for n in node.children.values():
                if not n.children:
                    continue
                print(
                    f"""
<li><a href="{n.label}/index.html">{str(n.label).capitalize()}</a></li>
""",
                    file=out,
                )
            print("</ul>", file=out)

        if any(n.item for n in node.children.values()):
            print("<h3>Articles</h3>\n<ul>", file=out)
            for n in node.children.values():
                article = n.item
                if not article:
                    continue
                print(
                    f"""
<li><a href="{n.label}.html">{article.cfg["title"]}</a></li>
""",
                    file=out,
                )
            print("</ul>", file=out)

        print("</body>\n</html>", file=out)


class Hubspot(Builder):

    name = "hubspot"

    def resolve_link(self, ctx: Context, link: Interlink) -> str:
        return ""

    def resolve_asset(self, ctx: Context, asset: Asset) -> str:
        return ""

    def build(self, articles: Iterator[Article]):
        print("TODO")


_builder_list: List[Type[Builder]] = [Html, Hubspot]

builders = {b.name: b for b in _builder_list}
