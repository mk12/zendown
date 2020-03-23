"""State of a Zendown project."""

import enum
from typing import List

from zendown.config import ProjectConfig
from zendown.files import FileSystem
from zendown.node import Node


class Kind(enum.Enum):
    ARTICLE = "articles"
    TEMPLATE = "templates"
    MACRO = "macros"
    TARGET = "targets"
    ASSET = "assets"


class Project:

    """Class storing all the information for a Zendown project."""

    def __init__(self, fs: FileSystem, cfg: ProjectConfig):
        self.fs = fs
        self.cfg = cfg
        self.nodes = {}

    @staticmethod
    def find() -> "Project":
        """Create a project by looking in the current directory and up."""
        fs = FileSystem.find()
        cfg = ProjectConfig.load(fs.file("zendown.yml"))
        return Project(fs, cfg)

    def query(self, kind: Kind, q: str) -> List[Node]:
        return self.fs.query(kind.value, q)
