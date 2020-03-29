"""Zendown project."""

import importlib.util
import os
from pathlib import Path
from types import ModuleType
from typing import Dict, Optional, Iterator, Union, cast

from zendown.article import Article
from zendown import macros
from zendown.config import ProjectConfig
from zendown.files import FileSystem
from zendown.tree import COLLISION, Collision, Label, Node, Ref
from zendown.zfm import Macro


class Project:
    def __init__(self, fs: FileSystem, cfg: ProjectConfig):
        self.fs = fs
        self.cfg = cfg
        self.name = cfg["project_name"]
        self.tree: Node[Article] = Node.root()
        self.articles_by_ref: Dict[Ref, Article] = {}
        self.articles_by_label: Dict[Label, Union[Article, Collision]] = {}
        self.macros: Optional[ModuleType] = None
        self.load_macros()
        self.scan_articles()

    @staticmethod
    def find() -> "Project":
        """Find the project based on the current working directory."""
        fs = FileSystem.find()
        cfg = ProjectConfig.load(fs.file("zendown.yml"))
        return Project(fs, cfg)

    def load_macros(self):
        """Load the project's macros.py file, if it exists."""
        f = self.fs.join("macros.py")
        if f.exists() and f.is_file():
            spec = importlib.util.spec_from_file_location("macros", f)
            self.macros = importlib.util.module_from_spec(spec)

    def get_macro(self, name: str) -> Optional[Macro]:
        """Get the macro function with the given name."""
        if not name:
            name = cast(str, self.cfg.get("default_macro"))
        if self.macros:
            macro = getattr(self.macros, name, None)
            if macro:
                return macro
        return getattr(macros, name, None)

    def scan_articles(self):
        """Locate all the articles in the project and populate the tree."""
        content_dir = self.fs.dir("content")
        self.tree = Node.root()
        for path, _, files in os.walk(content_dir):
            path = Path(path)
            for name in files:
                file_path = path / name
                if file_path.suffix != ".md":
                    continue
                node = self.tree
                rel_file_path = file_path.relative_to(content_dir)
                for part in str(rel_file_path.with_suffix("")).split("/"):
                    label = Label(part)
                    if label in node.children:
                        node = node.children[label]
                    else:
                        child = Node(label)
                        node.add_child(child)
                        node = child
                node.set_item(Article(file_path, node))
        self.tree.set_refs_recursively()
        for article in self.tree.all_items_recursively():
            self.articles_by_ref[article.node.ref] = article
            label = article.node.label
            if label in self.articles_by_label:
                self.articles_by_label[label] = COLLISION
            else:
                self.articles_by_label[label] = article

    def query(self, substr: str) -> Iterator[Article]:
        """Iterate over articles whose refs have the given substring."""
        for ref, article in self.articles_by_ref.items():
            if substr in str(ref):
                yield article
