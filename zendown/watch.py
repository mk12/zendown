"""File watching and live reloading server."""

from __future__ import annotations

import logging
import webbrowser
from pathlib import Path
from threading import Thread
from typing import Optional

import livereload
from livereload.handlers import LiveReloadHandler
from tornado.ioloop import IOLoop
from tornado.websocket import WebSocketError
from watchdog.events import FileModifiedEvent, FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from zendown.build import Builder
from zendown.project import Project


class Watcher:

    """Watch files for changes and rebuild using a given builder."""

    def __init__(self, project: Project, builder: Builder, server: Optional[Server]):
        self.fs = project.fs
        self.handler = Handler(project, builder, server)
        self.observer = Observer()
        self.server = server

    def run(self):
        # Have to pass str, not Path, otherwise it crashes with SIGILL.
        self.observer.schedule(self.handler, str(self.fs.root), recursive=False)
        for subdir in ["content", "assets", "includes"]:
            self.observer.schedule(
                self.handler, str(self.fs.join(subdir)), recursive=True
            )

        logging.info("running initial build")
        self.handler.build_all()
        logging.info("starting watcher")
        self.observer.start()
        try:
            if self.server:
                browse_after(self.server.url, 1)
                logging.info("starting server")
                self.server.run()
            self.observer.join()
        except KeyboardInterrupt:
            logging.info("quitting")
        finally:
            self.observer.stop()
            self.observer.join()


def browse_after(url: str, delay: int):
    """Open the browser to url after delay seconds."""
    Thread(target=lambda: webbrowser.open(url)).start()


class Handler(FileSystemEventHandler):

    """Handler for file system events on project files."""

    def __init__(self, project: Project, builder: Builder, server: Optional[Server]):
        super().__init__()
        self.project = project
        self.builder = builder
        self.server = server

    def matches(self, path: Path) -> bool:
        s = str(path)
        return (
            s == "macros.py"
            or s == "zendown.yml"
            or s.startswith("content/")
            or s.startswith("assets/")
            or s.startswith("includes/")
        )

    def on_any_event(self, event: FileSystemEvent):
        path = Path(event.src_path).relative_to(Path.cwd()).relative_to(self.project.fs.root)
        if not self.matches(path):
            return
        if isinstance(event, FileModifiedEvent):
            if path == Path("macros.py"):
                logging.info(
                    "%s %s: reload macros + build", event.src_path, event.event_type
                )
                self.project.load_macros()
            logging.info("%s %s: build", event.src_path, event.event_type)
        else:
            logging.info("%s %s: scan + build", event.src_path, event.event_type)
            self.project.scan_articles()
        self.project.unload_all()
        self.build_all()
        self.reload()

    def build_all(self):
        self.builder.build(self.project.all_articles())

    def reload(self):
        if self.server:
            self.server.reload_from_other_thread()


LIVE_RELOAD_PORT = 35729


class Server:

    """Live reloading server for HTML output."""

    def __init__(self, builder: Builder, port: int):
        assert builder.name == "html"
        self.host = "127.0.0.1"
        self.port = port
        self.server = livereload.Server()
        self.server.root = builder.fs.root
        self.server.default_filename = ""
        self.loop: Optional[IOLoop] = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def run(self):
        """Run the server."""
        logging.info("serving on %s", self.url)
        self.server.application(
            port=self.port,
            host=self.host,
            liveport=LIVE_RELOAD_PORT,
            debug=False,
            live_css=False,
        )
        self.loop = IOLoop.current()
        self.loop.start()

    def reload_from_other_thread(self):
        assert self.loop is not None
        self.loop.add_callback(self.reload)

    def reload(self):
        """Reload all connected browsers."""
        logging.info("reloading browsers")
        msg = {
            "command": "reload",
            "path": "*",
            "liveCSS": False,
            "liveImg": False,
        }
        for waiter in LiveReloadHandler.waiters.copy():
            try:
                waiter.write_message(msg)
            except WebSocketError:
                logging.error("error sending message", exc_info=True)
                LiveReloadHandler.waiters.remove(waiter)
