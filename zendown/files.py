"""File structure for Zendown projects."""

from pathlib import Path
from typing import Any, Mapping, Union

from zendown import defaults
from zendown.utils import fatal_error


def create_project(root: Path, project_name: str):
    """Create the default project files and directories in root."""

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
        fatal_error(f"'{ex.filename}' already exists")


class FileSystem:
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

    def join(self, path: Union[str, Path]) -> Path:
        """Get a path within the project."""
        return self.root / path

    def dir(self, path: Union[str, Path]) -> Path:
        """Get a directory in the project."""
        path = self.root / path
        if not path.exists():
            fatal_error(f"directory '{path}' not found")
        if not path.is_dir():
            fatal_error(f"'{path}' is not a directory")
        return path

    def file(self, path: Union[str, Path]) -> Path:
        """Get a file in the project."""
        path = self.root / path
        if not path.exists():
            fatal_error(f"file '{path}' not found")
        if not path.is_file():
            fatal_error(f"'{path}' is not a file")
        return path
