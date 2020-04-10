"""File watcher for automatic rebuilding."""

import logging
from pathlib import Path
import time

from watchdog.events import EVENT_TYPE_MODIFIED, FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from zendown.build import Builder
from zendown.project import Project


class Watcher:

    """Watch files for changes and rebuild using a given builder."""

    def __init__(self, project: Project, builder: Builder):
        self.fs = project.fs
        self.handler = Handler(project, builder)
        self.observer = Observer()

    def run(self):
        # Have to pass str, not Path, otherwise it crashes with SIGILL.
        self.observer.schedule(self.handler, str(self.fs.root), recursive=False)
        for subdir in ["content", "assets", "includes"]:
            self.observer.schedule(self.handler, str(self.fs.join(subdir)), recursive=True)
        self.observer.start()
        logging.info("started watcher")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()


class Handler(FileSystemEventHandler):

    def __init__(self, project: Project, builder: Builder):
        super().__init__()
        self.project = project
        self.builder = builder

    def matches(self, path: Path) -> bool:
        s = str(path)
        return (
            s == "macros.py" or
            s == "zendown.yml" or
            s.startswith("content/") or
            s.startswith("assets/") or
            s.startswith("includes/")
        )

    def on_any_event(self, event: FileSystemEvent):
        path = Path(event.src_path).relative_to(self.project.fs.root)
        if not self.matches(path):
            return
        if event.event_type == EVENT_TYPE_MODIFIED:
            logging.info("%s %s: build", event.src_path, event.event_type)
        else:
            logging.info("%s %s: scan + build", event.src_path, event.event_type)
            self.project.scan_articles()
        for article in self.project.all_resouces():
            article.load()
        self.builder.build(self.project.all_articles())
