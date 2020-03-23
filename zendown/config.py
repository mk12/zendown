"""Zendown configuration file parser."""

from io import StringIO
from os import PathLike
from pathlib import Path
from typing import Any, Optional, Type, TypeVar

import yaml

from zendown.utils import fatal_error

T = TypeVar('T', bound='Config')

class Config:

    """YAML configuration."""

    def __init__(self, path: Path, data: Any):
        self.path = path
        # self.parent = parent
        self.data = data
        self.validate()

    def validate(self):
        pass

    @classmethod
    def load(cls: Type[T], path: Path) -> T:
        """Load config from a file."""
        return cls.load_from(path, path)


    @classmethod
    def loads(cls: Type[T], path: Path, content: str) -> T:
        """Load config from a string."""
        return cls.load_from(path, StringIO(content))

    @classmethod
    def load_from(cls: Type[T], path: Path, content: PathLike) -> T:
        with open(content) as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as ex:
                fatal_error(f"cannot parse {path}: {ex}")
        return cls(path, data)
    
    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def get(self, key: str) -> Optional[Any]:
        return self.data.get(key)


class ProjectConfig(Config):

    REQUIRED = [
        "project_name",
    ]

    def validate(self):
        for key in self.REQUIRED:
            if key not in self.data:
                fatal_error(f"{self.path}: missing '{key}'")


class ArticleConfig(Config):

    REQUIRED = [
        "title",
    ]

    def validate(self):
        for key in self.REQUIRED:
            if key not in self.data:
                fatal_error(f"{self.path}: missing '{key}'")
