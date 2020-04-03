"""Build targets for projects."""

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Iterator, List, NamedTuple, Type

from zendown.article import Article
from zendown.files import FileSystem
from zendown.project import Project
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
    def resolve_article(self, ctx: Context, article: Article) -> str:
        """Resolve an article to a URL."""

    @abstractmethod
    def resolve_asset(self, ctx: Context, rel_path: str) -> str:
        """Resolve an asset path to a URL."""

    @abstractmethod
    def build(self, articles: Iterator[Article]):
        """Build the given articles."""


class Html(Builder):

    """Builds HTML web pages for direct browsing (no server needed)."""

    name = "html"

    def article_path(self, article: Article) -> str:
        pass

    def resolve_article(self, ctx: Context, article: Article) -> str:
        return "ARTICLE_PATH"

    def resolve_asset(self, ctx: Context, rel_path: str) -> str:
        path = "assets/" + rel_path
        if not self.project.fs.join(path).exists():
            logging.error("%s: asset %s does not exist", ctx.article.path, path)
        ref = ctx.article.node.ref
        assert ref
        to_root = "../" * (1 + len(ref.parts))
        return to_root + path

    def build(self, articles: Iterator[Article]):
        for article in articles:
            ctx = self.context(article)
            article.ensure_loaded()
            print(article.render_html(ctx))
            # TODO: pandoc step. add title, etc.
            # TODO: do builders need to have additional input, e.g. css
            # support/{html,hubspot}/style.cc etc.
            # another FileSystem object
            # ACTUALLY need to do recursive thing on tree,
            # just iterating articles won't create dirs and indexes.

        # def go(path: Path, node: Node[Article]):
        #     for article in node.items():
        #         pass

        #     for child in node.dirs():
        #         subdir = path / str(child.label)
        #         subdir.mkdir(exist_ok=True)
        #         go(subdir, child)

        # go(self.fs.root, self.project.tree)
        # catch rendererror


class Hubspot(Builder):

    name = "hubspot"

    def resolve_article(self, ctx: Context, article: Article) -> str:
        return ""

    def resolve_asset(self, ctx: Context, rel_path: str) -> str:
        return ""

    def build(self, articles: Iterator[Article]):
        print("TODO")


_builder_list: List[Type[Builder]] = [Html, Hubspot]

builders = {b.name: b for b in _builder_list}

# TODO: builder that lists cross-references between articles?
