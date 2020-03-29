"""Zendown flavored Markdown. It extends Markdown with macros."""

import re
from typing import Any, Callable, List, Optional, Union, cast

from mistletoe.block_token import BlockToken, Quote, tokenize
from mistletoe.span_token import Link, Image, InlineCode, SpanToken, RawText
from mistletoe.html_renderer import HTMLRenderer

from zendown.tree import COLLISION, Label, Ref

# Only import these for mypy.
if False:  # pylint: disable=using-constant-test
    # pylint: disable=unused-import,cyclic-import
    from zendown.article import Article
    from zendown.build import Builder
    from zendown.project import Project


Token = Union[SpanToken, BlockToken]


class Context:

    """Context passed to macros."""

    def __init__(self, builder: "Builder", project: "Project", article: "Article"):
        self.builder = builder
        self.project = project
        self.article = article
        self.renderer: Optional[ZFMRenderer] = None

    def render(self, token: Union[Token, List[Token]]) -> str:
        assert self.renderer
        if not isinstance(token, list):
            return self.renderer.render(token)
        if any(isinstance(c, BlockToken) for c in token):
            return "\n".join(self.renderer.render(c) for c in token)
        return "".join(self.renderer.render(c) for c in token)


# A macro takes a Context, argument string (between braces), and possibly a list
# of children (inside the blockquote following the colon).
Macro = Callable[[Context, str, List[BlockToken]], str]


class InlineMacro(SpanToken):
    pattern = re.compile(r"(?<!\\)@([a-z]+[a-z0-9]*)(?:{([^}]*)}|\b)")
    parse_inner = False

    def __init__(self, match):
        super().__init__(match)
        self.name = match.group(1)
        self.arg = match.group(2)


class BlockMacro(BlockToken):
    pattern = re.compile(r"^@([a-z]+[a-z0-9]*)({[^}]*})?:$")

    name = ""
    arg = ""

    def __init__(self, result):
        self.name, self.arg, lines = result
        super().__init__(lines, tokenize)

    @classmethod
    def start(cls, line):
        match = cls.pattern.match(line)
        if match is None:
            return False
        cls.name = match.group(1)
        cls.arg = match.group(2)
        return True

    @classmethod
    def read(cls, lines):
        next(lines)
        line_buffer = []
        for line in lines:
            if not Quote.start(line):
                break
            line_buffer.append(line)
        return cls.name, cls.arg, line_buffer


class RenderError(Exception):
    """An error that occurs during rendering."""


class ZFMRenderer(HTMLRenderer):

    """Renderer from ZFM to HTML."""

    def __init__(self, ctx: Context):
        super().__init__(InlineMacro, BlockMacro)
        ctx.renderer = self
        self.ctx = ctx
        self.inline_code_macro = ctx.project.cfg.get("inline_code_macro")

    def error(self, kind: str, arg: str) -> str:
        if self.ctx.builder.options.ignore_errors:
            return f"�{kind.upper()}: {arg}�"
        raise RenderError(f"{kind}: {arg}")

    def run_macro(self, name: str, arg: str, children: Any) -> str:
        macro = self.ctx.project.get_macro(name)
        if not macro:
            return self.error("undefined macro", name)
        return macro(self.ctx, arg, children)

    def render_inline_code(self, token: InlineCode) -> str:
        if self.inline_code_macro:
            return self.inline_code_macro(self.ctx, token.children[0].content, None)
        return super().render_inline_code(token)

    def render_inline_macro(self, token: InlineMacro) -> str:
        return self.run_macro(token.name, token.arg, None)

    def render_block_macro(self, token: BlockMacro) -> str:
        child = token.children[0]
        assert isinstance(child, Quote)
        return self.run_macro(token.name, token.arg, child.children)

    def render_link(self, token: Link) -> str:
        if "." not in token.target:
            article: Optional["Article"] = None
            if token.target.startswith("/"):
                ref = Ref.parse(token.target)
                article = self.ctx.project.articles_by_ref.get(ref)
            elif "/" not in token.target:
                label = Label(token.target)
                maybe_article = self.ctx.project.articles_by_label.get(label)
                if maybe_article is COLLISION:
                    return self.error("ambiguous article", token.target)
                article = cast(Optional["Article"], maybe_article)
            if article is not None:
                token.target = self.ctx.builder.resolve_article(self.ctx, article)
                if not token.children:
                    article.ensure_loaded()
                    assert article.cfg
                    token.children = [RawText(article.cfg["title"])]
        return super().render_link(token)

    def render_image(self, token: Image) -> str:
        if not (token.src.startswith("http://") or token.src.startswith("https://")):
            token.src = self.ctx.builder.resolve_asset(self.ctx, token.src)
        return super().render_image(token)
