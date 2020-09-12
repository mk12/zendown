"""Zendown project."""

from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, TypeVar

from zendown.article import Article
from zendown.config import Config
from zendown.files import FileSystem
from zendown.logs import fatal
from zendown.macro import Macro
from zendown.resource import Asset, Include, Resource
from zendown.tree import Label, Ref, Tree


class ProjectConfig(Config):

    required = {
        "project_name": "Unnamed Project",
    }

    optional = {
        "inline_code_macro": None,
        "smart_typography": False,
        "image_links": False,
        "image_title_from_alt": False,
    }


T = TypeVar("T", bound=Resource)


class Project:

    """A Zendown project.

    A project comprises a configuration file, a macros file, and trees of
    articles, assets, and include files.

    Projects should be created via Project.find(). This will:

    * Load the configuration file.
    * Load the macros files.
    * Scan the articles.

    Scanning articles only implies locating the files. None of the article files
    will be read until Article.load is called (by a Builder). Assets and include
    files are locating on demand by get_asset and get_include.

    The rationale for scanning all articles eagerly is that articles can link to
    others by label (rather than full ref), and macros/builders might wish to
    explore the entire article tree.
    """

    def __init__(self, fs: FileSystem, cfg: ProjectConfig):
        self.fs = fs
        self.cfg = cfg
        self.name = cfg["project_name"]
        self.macros: Optional[Dict[str, Macro]] = None
        self.assets: Tree[Asset] = Tree()
        self.includes: Tree[Include] = Tree()
        self.articles: Tree[Article] = Tree()
        self._inverse_links: Optional[Dict[Article, List[Article]]] = None
        self.load_macros()
        self.scan_articles()

    def __repr__(self) -> str:
        return f"Project(name={self.name!r}, path={self.fs.root!r})"

    @staticmethod
    def find() -> Project:
        """Find the project based on the current working directory."""
        fs = FileSystem.find()
        logging.info("found project %s", fs.root.resolve())
        cfg_path = fs.file("zendown.yml")
        if cfg_path is None:
            fatal("zendown.yml disappeared")
        cfg = ProjectConfig.load(cfg_path)
        cfg.validate()
        logging.debug("project config: %r", cfg)
        return Project(fs, cfg)

    def load_macros(self):
        """Load the project's macros.py file, if it exists."""
        f = self.fs.join("macros.py")
        if f.exists() and f.is_file():
            logging.info("loading macros file %s", f)
            spec = importlib.util.spec_from_file_location("macros", f)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore
            self.macros = getattr(module, "_macros", None)

    def get_macro(self, name: str) -> Optional[Macro]:
        """Get the macro with the given name."""
        if self.macros:
            return self.macros.get(name)
        return None

    def get_asset(self, ref: Ref[Asset]) -> Optional[Asset]:
        """Look up an asset in the project by ref."""
        asset = self.assets.by_ref.get(ref)
        if asset:
            return asset
        parts = (str(p) for p in ref.parts)
        path = self.fs.file(Path("assets").joinpath(*parts))
        if not path:
            return None
        logging.debug("found asset at %s", path)
        return self.assets.create(ref, Asset, path)

    def get_include(self, ref: Ref[Include]) -> Optional[Include]:
        """Look up an include file in the project by ref."""
        include = self.includes.by_ref.get(ref)
        if include:
            return include
        parts = (str(p) for p in ref.parts)
        rel_path = Path("includes").joinpath(*parts)
        if rel_path.suffix:
            logging.error("include path %r incorrectly has extension", rel_path)
            return None
        path = self.fs.file(rel_path.with_suffix(".md"))
        if not path:
            return None
        logging.debug("found include file at %s", path)
        return self.includes.create(ref, Include, path)

    def scan_articles(self):
        """Locate all the articles in the project and populate the tree."""
        content_dir = self.fs.dir("content")
        if not content_dir:
            return
        self.articles = Tree()
        for path_str, _, files in os.walk(content_dir):
            path = Path(path_str)
            for name in files:
                file_path = path / name
                if file_path.suffix not in (".md", ".yml"):
                    continue
                relative = file_path.relative_to(content_dir).with_suffix("")
                ref: Ref[Article] = Ref(tuple(Label(p) for p in relative.parts))
                self.articles.create(ref, Article, file_path)
                logging.debug("found article at %s", file_path)

    def all_articles(self) -> Iterable[Article]:
        """Iterate over all articles in the project."""
        return self.articles.by_ref.values()

    def all_resouces(self) -> Iterator[Resource]:
        """Iterate over all resources in the project."""
        yield from self.articles.by_ref.values()
        yield from self.assets.by_ref.values()
        yield from self.includes.by_ref.values()

    def unload_all(self):
        """Unload all resources in the project."""
        for resource in self.all_resouces():
            resource.unload()

    def query(self, substr: str) -> Iterator[Article]:
        """Iterate over articles whose refs have the given substring.

        If the query starts with "@", instead yields articles that have the
        given that value (excluding "@") in their "tags" config.
        """
        if substr.startswith("@"):
            tag = substr[1:]
            for article in self.articles:
                article.ensure_loaded()
                if tag in article.cfg["tags"]:
                    ref = article.node.ref
                    logging.debug("query %r matched article %s", substr, ref)
                    yield article
        else:
            for ref, article in self.articles.by_ref.items():
                if substr in str(ref):
                    logging.debug("query %r matched article %s", substr, ref)
                    yield article

    @property
    def inverse_links(self) -> Dict[Article, List[Article]]:
        """Return a mapping from articles to others that link to them.

        This causes all articles to be loaded, parsed, and resolved.
        """
        if self._inverse_links is None:
            self._inverse_links = {}
            for article in self.articles:
                self._inverse_links[article] = []
            for source in self.articles:
                source.ensure_resolved(self)
                for link in source.links:
                    dest = link.article
                    if dest is source:
                        continue
                    self._inverse_links[dest].append(source)
        return self._inverse_links
