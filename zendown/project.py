"""Zendown project."""

from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Iterator, Union

from zendown.article import Article
from zendown.config import Config
from zendown.files import FileSystem
from zendown.logs import fatal
from zendown.macro import Macro
from zendown.tree import Collision, Label, Node, Ref


class ProjectConfig(Config):

    required = {
        "project_name": "Unnamed Project",
    }

    optional = {
        "smart_typography": False,
        "inline_code_macro": None,
    }


class Project:

    """A Zendown project.

    A project comprises a configuration file, a tree of articles, a directory of
    assets, and optionally a macros file.

    Projects should be created via Project.find(). This will:

        * Load the configuration file.
        * Load the macros files.
        * Scan the articles.

    Scanning articles only implies locating the files. None of the article files
    will be read until Article.load is called (by a Builder).
    """

    def __init__(self, fs: FileSystem, cfg: ProjectConfig):
        self.fs = fs
        self.cfg = cfg
        self.name = cfg["project_name"]
        self.tree: Node[Article] = Node.root()
        self.articles_by_ref: Dict[Ref[Article], Article] = {}
        self.articles_by_label: Dict[Label[Article], Union[Article, Collision]] = {}
        self.macros: Optional[Dict[str, Macro]] = None
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
            spec.loader.exec_module(module) # type: ignore
            self.macros = getattr(module, "_macros", None)

    def get_macro(self, name: str) -> Optional[Macro]:
        """Get the macro with the given name."""
        if self.macros:
            return self.macros.get(name)
        return None

    def scan_articles(self):
        """Locate all the articles in the project and populate the tree."""
        content_dir = self.fs.dir("content")
        if not content_dir:
            return
        self.tree = Node.root()
        for path_str, _, files in os.walk(content_dir):
            path = Path(path_str)
            for name in files:
                file_path = path / name
                if file_path.suffix != ".md":
                    continue
                node = self.tree
                rel_file_path = file_path.relative_to(content_dir)
                for part in str(rel_file_path.with_suffix("")).split("/"):
                    label: Label[Article] = Label(part)
                    if label in node.children:
                        node = node.children[label]
                    else:
                        child = Node(label)
                        node.add_child(child)
                        node = child
                logging.debug("found article at %s", file_path)
                node.set_item(Article(file_path, node))
        self.tree.set_refs_recursively()
        self.articles_by_ref = self.tree.items_by_ref()
        self.articles_by_label = self.tree.items_by_label()

    def query(self, substr: str) -> Iterator[Article]:
        """Iterate over articles whose refs have the given substring."""
        for ref, article in self.articles_by_ref.items():
            if substr in str(ref):
                logging.debug("query %r matched article %r", substr, ref)
                yield article
