"""Zendown flavored Markdown. It extends Markdown with macros."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional, TYPE_CHECKING, cast

from mistletoe.block_token import BlockToken, HTMLBlock, Heading, Quote, tokenize
from mistletoe.span_token import Link, HTMLSpan, Image, InlineCode, SpanToken, RawText
from mistletoe.html_renderer import HTMLRenderer

from zendown.macro import Context, MacroError
from zendown.tree import COLLISION, Label, Ref

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from zendown.article import Article


def smartify(text: str) -> str:
    """Augment text with smart typography.

    This replaces dumb quotes with curly quotes, "..." with ellipses, and "--"
    with em dashes.
    """
    text = re.sub(r"([a-zA-Z0-9.,?!;:\'\"])\"", r"\1”", text)
    text = text.replace(r'"', r"“")
    text = re.sub(r"([a-zA-Z0-9.,?!;:\'\"])'", r"\1’", text)
    text = text.replace(r"'", r"‘")
    text = text.replace(r"...", r"…")
    text = text.replace(r"--", r"—")
    return text


def set_heading_identifier(heading: Heading):
    """Sets the identifier field on heading.

    For example:

        # Some heading {#some-id}

    This heading would have an identifer of "some-id". If this syntax is not
    present, the identifier will be None.
    """
    heading.identifier = None
    if heading.children:
        last = heading.children[-1]
        if isinstance(last, RawText):
            match = re.search(r" {#([^ }]+)}(?:$|\n)", last.content)
            if match:
                last.content = last.content[: match.start()]
                heading.identifier = match.group(1)


def patched_heading_init(self, *args, **kwargs):
    """Patched version of Heading.__init__ that sets the identifier."""
    original_heading_init(self, *args, **kwargs)
    set_heading_identifier(self)


# Monkey patch mistletoe.block_token.Heading.__init__.
original_heading_init = Heading.__init__
Heading.__init__ = patched_heading_init


class InlineMacro(SpanToken):
    pattern = re.compile(r"(?<!\\)@([a-z]+[a-z0-9]*)(?:{([^}]*)}|\b)")
    parse_inner = False

    def __init__(self, match):
        super().__init__(match)
        self.name = match.group(1)
        self.arg = match.group(2)


class BlockMacro(BlockToken):
    pattern = re.compile(r"^@([a-z]+[a-z0-9]*)({[^}]*})?(:)?$")

    name = ""
    arg = ""
    colon = ""

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
        cls.colon = match.group(3)
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


class ZFMRenderer(HTMLRenderer):

    """Renderer from ZFM to HTML."""

    def __init__(self, ctx: Context):
        super().__init__(InlineMacro, BlockMacro)
        ctx.renderer = self
        self.ctx = ctx
        self.inline_code_macro = ctx.project.cfg["inline_code_macro"]
        self.smart_typography = ctx.project.cfg["smart_typography"]

    def error(self, kind: str, *info: str) -> str:
        info_str = ": ".join(info)
        logging.error("%s: %s: %s", self.ctx.article.path, kind, info_str)
        return f"�{kind.upper()}: {info_str}�"

    def run_macro(self, name: str, arg: str, children: Any) -> str:
        macro = self.ctx.project.get_macro(name)
        if not macro:
            return self.error("undefined macro", name)
        try:
            return macro(self.ctx, arg, children)
        except MacroError as ex:
            return self.error("macro error", name, str(ex))

    def render_html_span(self, token: HTMLSpan) -> str:
        if token.content.startswith("<!--"):
            return ""
        return super().render_html_span(token)

    def render_html_block(self, token: HTMLBlock) -> str:
        if token.content.startswith("<!--"):
            return ""
        return super().render_html_block(token)

    def render_heading(self, token: Heading) -> str:
        template = '<h{level} id="{id}">{inner}</h{level}>'
        inner = self.render_inner(token)
        return template.format(level=token.level, id=token.identifier, inner=inner)

    def render_inline_code(self, token: InlineCode) -> str:
        if self.inline_code_macro:
            text = token.children[0].content
            return self.run_macro(self.inline_code_macro, text, None)
        return super().render_inline_code(token)

    def render_inline_macro(self, token: InlineMacro) -> str:
        return self.run_macro(token.name, token.arg, None)

    def render_block_macro(self, token: BlockMacro) -> str:
        # TODO might have no children
        child = token.children[0]
        assert isinstance(child, Quote)
        return self.run_macro(token.name, token.arg, child.children)

    def render_raw_text(self, token: RawText) -> str:
        if self.smart_typography:
            token.content = smartify(token.content)
        return super().render_raw_text(token)

    def render_link(self, token: Link) -> str:
        # TODO: anchors handled in Ref parse (but also allow labelonly#anchor)
        if "." not in token.target:
            path, anchor = token.target, ""
            if "#" in path:
                i = path.index("#")
                path, anchor = path[:i], path[i:]
            article: Optional[Article] = None
            if path.startswith("/"):
                ref: Ref[Article] = Ref.parse(path)
                article = self.ctx.project.articles_by_ref.get(ref)
            elif "/" not in path:
                label: Label[Article] = Label(path)
                maybe_article = self.ctx.project.articles_by_label.get(label)
                if maybe_article is COLLISION:
                    return self.error("ambiguous article", path)
                article = cast(Optional["Article"], maybe_article)
            if article is not None:
                url = self.ctx.builder.resolve_article(self.ctx, article)
                token.target = url + anchor
                if not token.children:
                    article.ensure_loaded()
                    assert article.cfg
                    token.children = [RawText(article.cfg["title"])]
            # TODO: FAIL IF ARTICLE+ANCHOR DOESN'T EXIST, don't silently leave.
        return super().render_link(token)

    def render_image(self, token: Image) -> str:
        if not (token.src.startswith("http://") or token.src.startswith("https://")):
            token.src = self.ctx.builder.resolve_asset(self.ctx, token.src)
        return super().render_image(token)
