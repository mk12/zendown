"""Logging configuration."""

import logging
from logging import Formatter, LogRecord, StreamHandler
import sys
from typing import Dict, TextIO, NoReturn


class ColorFormatter(Formatter):

    """Log formatter that prints bold, colorized level names."""

    COLORS = {
        logging.FATAL: 31,  # red
        logging.ERROR: 31,  # red
        logging.WARNING: 33,  # yellow
        logging.INFO: 32,  # green
        logging.DEBUG: 35,  # magenta
    }

    FORMAT = "%(message)s"

    def __init__(self, use_color: bool):  # pylint: disable=super-init-not-called
        self.default = Formatter(f"%(levelname)s: {self.FORMAT}")
        self.formatters: Dict[int, Formatter] = {}
        if use_color:
            for level in self.COLORS:
                code = self.COLORS[level]
                fmt = f"\x1b[{code};1m%(levelname)s:\x1b[0m {self.FORMAT}"
                self.formatters[level] = Formatter(fmt)

    def format(self, record: LogRecord) -> str:
        formatter = self.formatters.get(record.levelno, self.default)
        return formatter.format(record)


class ExitStreamHandler(StreamHandler):

    """Stream handler that exits the program after severe logs.

    By default, it exits with status 1 after emitting a log record at the FATAL
    level or higher. This threshold can be configured by the exit_level setting.
    """

    def __init__(self, stream: TextIO = None, exit_level: int = logging.FATAL):
        super().__init__(stream)
        self.exit_level = exit_level

    def emit(self, record: LogRecord):
        super().emit(record)
        if record.levelno >= self.exit_level:
            sys.exit(1)


def setup_logging(stream: TextIO, log_level: int, exit_level: int):
    """Set up the root logger.

    Uses color if the stream is not a TTY. The log_level must not be higher than
    exit_level (exiting before printing makes no sense), and the exit_level must
    not be higher than FATAL (fatal logs should always cause an exit).
    """
    assert log_level <= exit_level
    assert exit_level <= logging.FATAL
    logger = logging.getLogger()
    logger.setLevel(log_level)
    handler = ExitStreamHandler(sys.stderr, exit_level)
    handler.setFormatter(ColorFormatter(use_color=stream.isatty()))
    logger.addHandler(handler)
    # FATAL and CRITICAL are the same. I prefer the label FATAL.
    logging.addLevelName(logging.FATAL, "FATAL")


def fatal(msg: str, *args, **kwargs) -> NoReturn:
    """A wrapper around logging.fatal.

    Fatal logs in this program always cause a sys.exit(-1). This wrapper is
    provided to document that fact, and to enable a NoReturn typing so that
    tools know code following a fatal log is unreachable.
    """
    logging.fatal(msg, *args, **kwargs)
    assert False  # convince mypy it will not return
