"""Configuration file parser."""

from abc import ABC
from io import StringIO
from pathlib import Path
from typing import Any, List, Optional, TextIO, Type, TypeVar

import yaml

from zendown.utils import fatal_error

T = TypeVar("T", bound="Config")


class Config(ABC):

    """YAML configuration."""

    REQUIRED: List[str] = []

    def __init__(self, path: Path, data: Any):
        self.path = path
        self.data = data
        self.validate()

    def validate(self):
        for key in self.REQUIRED:
            if key not in self.data:
                fatal_error(f"{self.path}: missing '{key}'")

    @classmethod
    def load(cls: Type[T], path: Path) -> T:
        """Load config from a file."""
        with open(path) as f:
            return cls.load_from(path, f)

    @classmethod
    def loads(cls: Type[T], path: Path, content: str) -> T:
        """Load config from a string."""
        return cls.load_from(path, StringIO(content))

    @classmethod
    def load_from(cls: Type[T], path: Path, content: TextIO) -> T:
        try:
            data = yaml.safe_load(content)
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


class ArticleConfig(Config):

    REQUIRED = [
        "title",
    ]
