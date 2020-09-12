"""Build targets for projects."""

import html
import json
import logging
import os.path
import shlex
import subprocess
import webbrowser
from abc import ABC, abstractmethod
from importlib import resources
from pathlib import Path
from shutil import rmtree
from typing import (
    Any,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    TextIO,
    Type,
)
from urllib.parse import quote

import pyperclip
from jinja2 import Environment, PackageLoader, escape, select_autoescape

from zendown import templates
from zendown.article import Article, Index, Interlink
from zendown.config import Config
from zendown.files import FileSystem
from zendown.project import Project
from zendown.resource import Asset
from zendown.tree import Node
from zendown.zfm import Context, RenderOptions, ZFMRenderer


class Options(NamedTuple):

    """Options for building."""


class Builder(ABC):

    """Abstract base class for all builders."""

    name: str
    supports_watch: bool
    needs_fs: bool

    def __init__(self, project: Project, options: Options):
        self.project = project
        self.options = options
        if self.needs_fs:
            out_dir = project.fs.join(Path("out") / self.name)
            self.fs = FileSystem(out_dir)

    def clean(self):
        """Delete the contents of the output directory."""
        if self.needs_fs:
            rmtree(self.fs.root, ignore_errors=True)

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
        if self.needs_fs:
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
    def _build(self, articles: Sequence[Article]):
        ...

    @abstractmethod
    def _open(self, article: Optional[Article]):
        ...


class Html(Builder):

    """Builds HTML web pages for direct browsing (no server needed)."""

    name = "html"
    supports_watch = True
    needs_fs = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = Environment(
            loader=PackageLoader("zendown", "templates"),
            autoescape=select_autoescape(["html"]),
        )
        self.css = resources.open_text(templates, "style.css").read()
        self.index_template = self.env.get_template("index.html.jinja")
        self.article_template = self.env.get_template("article.html.jinja")

    def node_path(self, node: Optional[Node[Article]]) -> Path:
        slugs: List[str] = []
        while node and not node.is_root():
            slugs.insert(0, Index(node).slug)
            node = node.parent
        return Path("/".join(slugs))

    def article_path(self, article: Article) -> Path:
        if article.is_index():
            assert article.node.parent
            return self.index_path(article.node.parent)
        path = self.node_path(article.node.parent) / article.slug
        return self.fs.join(path.with_suffix(".html"))

    def index_path(self, node: Node[Article]) -> Path:
        return self.fs.join(self.node_path(node) / "index.html")

    def _resolve_link(self, ctx: Context, link: Interlink) -> str:
        if link.article is ctx.article:
            rel = ""
        else:
            source = self.article_path(ctx.article).parent
            dest = self.article_path(link.article)
            rel = quote(os.path.relpath(dest, source))
        if link.section:
            return f"{rel}#{link.section.node.label}"
        return rel or "#"

    def _resolve_asset(self, ctx: Context, asset: Asset) -> str:
        path = asset.path
        if not self.project.fs.join(path).exists():
            logging.error("%s: asset %s does not exist", ctx.article.path, path)
        return self.relative_base(ctx.article.node, -1) + quote(str(path))

    def _build(self, articles: Sequence[Article]):
        assets = self.fs.join("assets")
        if not assets.exists():
            relative = os.path.relpath(self.project.fs.join("assets"), self.fs.root)
            assets.symlink_to(relative, target_is_directory=True)
        with open(self.fs.join("style.css"), "w") as f:
            f.write(self.css)
        parents: List[Node[Article]] = []
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
        done: Set[Node[Article]] = set()
        while parents:
            node = parents.pop()
            if node in done:
                continue
            done.add(node)
            if node.parent:
                parents.append(node.parent)
            path = self.index_path(node)

            # I thought this should be unnecessary based on the order of
            # processing nodes, but there were errors and this fixed it.
            path.parent.mkdir(parents=True, exist_ok=True)

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
        body = None
        article = index.article
        if article:
            ctx = self.context(article)
            article.ensure_loaded()
            if not article.cfg_only:
                article.ensure_resolved(self.project)
                with ZFMRenderer(ctx, RenderOptions(shift_headings_by=1)) as r:
                    body = article.render(r)
        root = index.node.is_root()
        vals = {
            "base": self.relative_base(index.node),
            "root": root,
            "title": index.title,
            "body": body,
        }
        if body:
            out.write(self.index_template.render(**vals))
            return

        def make_tree(n: Node[Article], rel: str) -> str:
            items = []
            for child in n.children.values():
                article = child.item
                if article and not article.is_index():
                    items.append(
                        f'<a href="{rel}{article.slug}.html">{escape(article.title)}</a>'
                    )
            for child in n.children.values():
                if not child.children:
                    continue
                assert not child.item
                i = Index(child)
                items.append(
                    f'<a href="{rel}{i.slug}/index.html">{escape(i.title)}</a>'
                    + make_tree(child, f"{rel}{i.slug}/")
                )
            items_str = "\n".join(f"<li>{item}</li>" for item in items)
            return f"<ul>\n{items_str}</ul>\n"

        vals["body"] = make_tree(index.node, "")
        out.write(self.index_template.render(**vals))

    @staticmethod
    def relative_base(node: Node, adjust: int = 0) -> str:
        return "../" * (len(node.ref.parts) + adjust)

    def _open(self, article: Optional[Article]):
        if article:
            path = self.article_path(article)
        else:
            path = self.index_path(self.project.articles.root)
        webbrowser.open(path.absolute().as_uri())


class Hubspot(Builder):

    name = "hubspot"
    supports_watch = False
    needs_fs = False

    def __init__(self, project: Project, options: Options):
        super().__init__(project, options)
        self.company_id = self.config(project.cfg, "hubspot_company_id")
        self.base_url = self.config(project.cfg, "hubspot_base_url").rstrip("/")
        if not (
            self.base_url.startswith("http://") or self.base_url.startswith("https://")
        ):
            logging.fatal(
                "%s: hubspot_base_url must start with http:// or https://",
                project.cfg.path,
            )
        self.asset_base = self.config(project.cfg, "hubspot_asset_base").rstrip("/")

    def config(self, cfg: Config, key: str) -> Any:
        value = cfg.get(key)
        if value is None:
            logging.fatal(
                "%s: missing %r, required by %s builder", cfg.path, key, self.name
            )
        return value

    def article_url(self, article: Article) -> str:
        return f"{self.base_url}/{article.slug}"

    def index_url(self, node: Node[Article]) -> str:
        return f"{self.base_url}/{Index(node).slug}"

    def article_edit_url(self, article: Article) -> str:
        article.ensure_loaded()
        assert article.cfg
        article_id = self.config(article.cfg, "hubspot_id")
        return f"https://app.hubspot.com/knowledge/{self.company_id}/edit/{article_id}"

    def article_api_url(self, article: Article) -> str:
        article.ensure_loaded()
        assert article.cfg
        article_id = self.config(article.cfg, "hubspot_id")
        return f"https://api.hubspot.com/knowledge-content/v1/knowledge-articles/{article_id}?portalId={self.company_id}"

    def _resolve_link(self, ctx: Context, link: Interlink) -> str:
        url = self.article_url(link.article)
        if link.section:
            return f"{url}#{link.section.node.label}"
        return url

    def _resolve_asset(self, ctx: Context, asset: Asset) -> str:
        path = self.asset_base / asset.path.relative_to(self.project.fs.join("assets"))
        return f"{self.base_url}/hs-fs/hubfs/{quote(str(path))}"

    def _build(self, articles: Sequence[Article]):
        if not articles:
            return
        if len(articles) > 1:
            logging.fatal("%s builder only supports building 1 article", self.name)
        article = articles[0]
        article.ensure_resolved(self.project)
        ctx = self.context(article)
        with ZFMRenderer(ctx, RenderOptions(shift_headings_by=2)) as r:
            body = article.render(r)
        preamble = f"<h1>{html.escape(article.title)}</h1>\n"
        assert article.cfg
        subtitle = article.cfg["subtitle"] or ""
        preamble += f"<h2>{html.escape(subtitle)}</h2>\n"
        pyperclip.copy(preamble + body)

    def _open(self, article: Optional[Article]):
        webbrowser.open(self.article_edit_url(article))

    def _old_build(self, articles: Sequence[Article]):
        if not articles:
            return
        if len(articles) > 1:
            logging.fatal("%s builder only supports building 1 article", self.name)
        article = articles[0]
        edit_url = self.article_edit_url(article)
        print(
            f"""
Zendown will open your browser to {edit_url}

Once there (and logged in), follow these steps:

1. Right click on the page and choose "Inspect Element".
2. Switch to the "Network" tab in the developer tools.
3. Click on the "XHR" filter label.
4. Type a letter in the article body. An entry should show up in Network.
5. Right click the entry and select "Copy as cURL".

When you're ready, press enter.
"""
        )
        reply = input()
        if reply.lower() == "q":
            logging.fatal("aborting")
        webbrowser.open(edit_url)
        reply = input("Have you completed steps 1-5? [y/N] ")
        if reply.lower() != "y":
            logging.fatal("aborting")
        curl = shlex.split(pyperclip.paste())
        data_idx = curl.index("--data-binary")
        if not (len(curl) > 20 and curl[0] == "curl" and data_idx >= 1):
            logging.fatal("failed to parse cURL; are you sure you copied it?")
        article.ensure_resolved(self.project)
        ctx = self.context(article)
        with ZFMRenderer(ctx, RenderOptions(shift_headings_by=2)) as r:
            body = article.render(r)
        print(f"Using the following content:\n\n{body}\n")
        reply = input("Continue? [y/N] ")
        if reply.lower() != "y":
            logging.fatal("aborting")
        print("[[[" + repr(curl[data_idx + 1]) + "]]]")
        curl[data_idx + 1] = json.dumps(
            {"articleBody": body.strip(), "generator": "TINYMCE"}, separators=(",", ":")
        )
        cmd_str = "\n".join(curl)
        print(f"About to run the following command:\n\n{cmd_str}\n")
        reply = input("Continue? [y/N] ")
        if reply.lower() != "y":
            logging.fatal("aborting")
        subprocess.call(curl)


_builder_list: List[Type[Builder]] = [Html, Hubspot]

builders = {b.name: b for b in _builder_list}
