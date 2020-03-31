"""Configuration file parser."""

from abc import ABC
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Set, TextIO, Type, TypeVar

import yaml

from zendown.utils import fatal_error

T = TypeVar("T", bound="Config")


class Config(ABC):

    """YAML configuration."""

    REQUIRED: Set[str] = set()
    OPTIONAL: Dict[str, Any] = {}

    def __init__(self, path: Path, data: Dict[str, Any]):
        self.path = path
        self.data = data
        self.validate()

    def validate(self):
        for key in self.REQUIRED:
            if key not in self.data:
                fatal_error(f"{self.path}: missing '{key}'")
        for key in self.data:
            if key not in self.REQUIRED and key not in self.OPTIONAL:
                fatal_error(f"{self.path}: invalid key '{key}'")

    @classmethod
    def load(cls: Type[T], path: Path, defaults: Dict[str, Any] = None) -> T:
        """Load config from a file."""
        with open(path) as f:
            return cls.load_from(path, f, defaults)

    @classmethod
    def loads(
        cls: Type[T], path: Path, content: str, defaults: Dict[str, Any] = None
    ) -> T:
        """Load config from a string."""
        return cls.load_from(path, StringIO(content), defaults)

    @classmethod
    def load_from(
        cls: Type[T], path: Path, content: TextIO, defaults: Dict[str, Any] = None
    ) -> T:
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as ex:
            fatal_error(f"cannot parse {path}: {ex}")
        if not isinstance(data, dict):
            fatal_error(f"invalid YAML in {path}: {type(data)}")
        if defaults:
            data = {**defaults, **data}
        return cls(path, data)

    def __getitem__(self, key: str) -> Any:
        if key in self.REQUIRED:
            return self.data[key]
        if key in self.OPTIONAL:
            return self.data.get(key, self.OPTIONAL[key])
        raise ValueError(f"Invalid key {key}")


class ProjectConfig(Config):

    REQUIRED = {
        "project_name",
    }

    OPTIONAL = {
        "inline_code_macro": None,
        "smart_typography": False,
    }


class ArticleConfig(Config):

    REQUIRED = {
        "title",
        "slug",
    }
