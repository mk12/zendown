"""File structure for Zendown projects."""

import os
from pathlib import Path
from typing import Iterator, Mapping, Optional

from zendown import config, defaults
from zendown.node import Node
from zendown.utils import fatal_error


def create_project(root: Path, project_name: str):
    """Create the default project files and directories in root."""

    def create(root: Path, structure: Mapping[str, any]):
        for name, val in structure.items():
            path = root / name
            if type(val) is dict:
                path.mkdir()
                create(path, val)
            elif type(val) is str:
                with open(path, "w") as f:
                    f.write(val)
            elif type(val) is bytes:
                with open(path, "wb") as f:
                    f.write(val)
            else:
                raise Exception(f"unexpected type: {type(val)}")
    try:
        create(root, defaults.structure(project_name))
    except FileExistsError as ex:
        fatal_error(f"'{ex.filename}' already exists")


class FileSystem:

    """Zendown project directory in the file system."""

    def __init__(self, root: Path):
        self.root = root

    @staticmethod
    def find() -> "FileSystem":
        """Find the project root by searching for a zendown.yml file."""
        path = Path.cwd()
        while True:
            if (path / "zendown.yml").exists():
                return FileSystem(path)
            if path == path.parent:
                fatal_error("not in a Zendown project")
            path = path.parent

    def dir(self, path: Path) -> Path:
        """Get a directory in the project."""
        path = self.root / path
        if not path.exists():
            fatal_error(f"directory '{path}' not found")
        if not path.is_dir():
            fatal_error(f"'{path}' is not a directory")
        return path

    def file(self, path: Path) -> Path:
        """Get a file in the project."""
        path = self.root / path
        if not path.exists():
            fatal_error(f"file '{path}' not found")
        if not path.is_file():
            fatal_error(f"'{path}' is not a file")
        return path

    def query(self, kind: str, q: str) -> Iterator[Node]:
        dir = self.dir(Path(kind))
        for path, _, files in os.walk(dir):
            path = Path(path)
            for f in files:
                if f.startswith("."):
                    continue
                p = path / f
                ref = str(p.relative_to(self.root).with_suffix(""))
                if not ref.startswith(kind + "/" + q):
                    continue
                yield Node(path / f, ref)
