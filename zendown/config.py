"""Configuration file parser."""

import logging
from abc import ABC, abstractproperty
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, TextIO, Type, TypeVar

import yaml

T = TypeVar("T", bound="Config")


class Config(ABC):

    """Abstract base class for YAML configuration.

    Subclasses should override abstract properties "required" and "optional".

    Example usage:

        # Assuming MyConfig is a subclass of Config:
        cfg = MyConfig.load(Path("/path/to/config.yml"))
        cfg.validate()

    Note that the creator must call validate(). They can optionally pass extra
    defaults as keyword arguments. This is useful if the default is
    context-dependent (static defaults can go in the required/optional dicts).
    """

    def __init__(self, path: Path, data: Mapping[str, Any]):
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

        Extra defaults can be passed for keys as keyword arguments. They will
        override the defaults from the "required" and "optional" properties.
        """
        for key in self.required:
            if key not in self.data:
                logging.error("%s: missing %r", self.path, key)
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
            data = {}
        if not isinstance(data, dict):
            logging.error("invalid YAML in %s: %s", path, type(data))
            data = {}
        return cls(path, data)

    def __getitem__(self, key: str) -> Any:
        """Get a configuration value."""
        return self.data[key]

    def get(self, key: str) -> Optional[Any]:
        """Get a configuration value, or None if it does not exist."""
        return self.data.get(key)
