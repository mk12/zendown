"""Configuration file parser."""

from abc import ABC, abstractproperty
from io import StringIO
import logging
from pathlib import Path
from typing import Any, Dict, TextIO, Type, TypeVar

import yaml


T = TypeVar("T", bound="Config")


class Config(ABC):

    """Abstract base class for YAML configuration."""

    def __init__(self, path: Path, data: Dict[str, Any]):
        self.path = path
        self.data = data

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"{name}(path={self.path!r}, data={self.data!r})"

    @abstractproperty
    def required(self) -> Dict[str, Any]:
        """Required configuration keys and their defaults."""

    @abstractproperty
    def optional(self) -> Dict[str, Any]:
        """Optional configuration keys and their defaults."""

    def validate(self, **defaults: Any):
        """Validate the loaded configuration.

        This must be called manually after creating an instance.

        Extra defaults can be passed for keys whose default is dynamically
        determined. They will override the defaults from the required and
        optional properties.
        """
        for key in self.required:
            if key not in self.data:
                logging.error("%s: missing %r", self.path, key)
        for key in self.data:
            if key not in self.required and key not in self.optional:
                logging.warning("%s: unexpected key %r", self.path, key)
        self.data = {**self.required, **self.optional, **defaults, **self.data}

    @classmethod
    def load(cls: Type[T], path: Path) -> T:
        """Load configuration from a file."""
        with open(path) as f:
            return cls.load_from(path, f)

    @classmethod
    def loads(cls: Type[T], path: Path, content: str) -> T:
        """Load configuration from a string."""
        return cls.load_from(path, StringIO(content))

    @classmethod
    def load_from(cls: Type[T], path: Path, content: TextIO) -> T:
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as ex:
            logging.error("cannot parse %s: %s", path, ex)
        if not isinstance(data, dict):
            logging.error("invalid YAML in %s: %s", path, type(data))
            data = {}
        return cls(path, data)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]
