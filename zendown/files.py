"""File structure for Zendown projects."""

import logging
import os.path
from pathlib import Path
from typing import Any, Mapping, Optional, Union

from zendown import defaults
from zendown.logs import fatal


def create_project(root: Path, project_name: str):
    """Create the default project files and directories in root.

    Exits with a fatal log if root already exists.
    """

    def create(root: Path, structure: Mapping[str, Any]):
        for name, val in structure.items():
            path = root / name
            if isinstance(val, dict):
                path.mkdir()
                create(path, val)
            elif isinstance(val, str):
                with open(path, "w") as f:
                    f.write(val)
            elif isinstance(val, bytes):
                with open(path, "wb") as bf:
                    bf.write(val)
            else:
                raise Exception(f"unexpected type: {type(val)}")

    try:
        create(root, defaults.structure(project_name))
    except FileExistsError as ex:
        fatal("%s already exists", ex.filename)


class FileSystem:
    def __init__(self, root: Path):
        self.root = root

    def __repr__(self) -> str:
        return f"FileSystem(root={self.root!r})"

    @staticmethod
    def find() -> "FileSystem":
        """Find the project root by searching for a zendown.yml file.

        Exits with a fatal log if it cannot find the file.
        """
        path = Path.cwd()
        while True:
            config = path / "zendown.yml"
            if config.exists() and config.is_file():
                # Get the relative path to avoid showing absolute paths
                # everywhere (e.g. in log messages). Must use os.path.relpath
                # rather than Path.relative_to because the latter does not go up
                # directories (i.e. use "..").
                relative = Path(os.path.relpath(path, Path.cwd()))
                return FileSystem(relative)
            if path == path.parent:
                fatal("not in a zendown project")
            path = path.parent

    def join(self, path: Union[str, Path]) -> Path:
        """Get a path within the project."""
        return self.root / path

    def dir(self, path: Union[str, Path]) -> Optional[Path]:
        """Get a directory in the project that is expected to exist.

        Logs an error and returns None if it does not exist.
        """
        path = self.root / path
        if not path.exists():
            logging.error("directory %s not found", path)
            return None
        if not path.is_dir():
            logging.error("%s is not a directory", path)
            return None
        return path

    def file(self, path: Union[str, Path]) -> Optional[Path]:
        """Get a file in the project that is expected to exist.

        Logs an error and returns None if it does not exist.
        """
        path = self.root / path
        if not path.exists():
            logging.error("file %s not found", path)
            return None
        if not path.is_file():
            logging.error("%s is not a file", path)
            return None
        return path
