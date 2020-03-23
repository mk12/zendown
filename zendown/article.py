"""Zendown articles and templates."""

from pathlib import Path

from jinja2 import Template

from zendown.config import ArticleConfig

class Article:

    """A partially parsed YAML/Jinja2/Pandoc hybrid document."""

    def __init__(self, path: Path):
        self.path = path
        # self.ref = 
        self.cfg = None
        self.body = None

    def reload(self):
        with open(self.path) as f:
            head = ""
            for line in f:
                if line.rstrip() == "---":
                    break
                head += line
            body = f.read()
        self.cfg = ArticleConfig.loads(self.path, head)
        self.body = body

    @staticmethod
    def load(path: Path) -> "Article":
        a = Article(path)
        a.reload()
        return a

    def render(self) -> str:
        """Render the article body using Jinja2."""
