"""Zendown flavored Markdown. It extends Markdown with macros."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, List, NamedTuple, Optional

from mistletoe import block_token, span_token
from mistletoe.block_token import BlockToken, Document, Heading, HTMLBlock, Quote
from mistletoe.html_renderer import HTMLRenderer
from mistletoe.span_token import HTMLSpan, Image, InlineCode, Link, RawText, SpanToken

from zendown.macro import Context, Kind, MacroError
from zendown.tokens import Token, link, raw_text, strip_comments

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from zendown.article import Article


def set_zfm_tokens():
    """Reset the mistletoe tokens to the ones ZFM token set.

    Mistletoe is designed to use renderes as context managers, adding tokens on
    entry and reseting them on exit. This doesn't work well for Zendown because
    parsing and rendering are decoupled. We need to parse before rendering, but
    we also might parse in the middle of rendering (in which case we don't want
    to reset tokens immediately afterwards!). The hacky solution is just to call
    this function before tokenizing to ensure the right tokens are there.
    """
    block_token.reset_tokens()
    span_token.reset_tokens()
    block_token.add_token(HTMLBlock)
    block_token.add_token(ExtendedHeading)
    block_token.add_token(BlockMacro)
    span_token.add_token(HTMLSpan)
    span_token.add_token(InlineMacro)


def parse_document(raw: str) -> Document:
    """Parse a ZFM document."""
    set_zfm_tokens()
    doc = Document(raw)
    strip_comments(doc)
    return doc


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


class ExtendedHeading(Heading):

    """Heading token extended with id attribute support.

    Example:

        # Some heading {#some-id}

    This heading would have an id of "some-id".
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.identifier = None
        if self.children:
            last = self.children[-1]
            if isinstance(last, RawText):
                match = re.search(r" {#([^ }]+)}(?:$|\n)", last.content)
                if match:
                    last.content = last.content[: match.start()]
                    self.identifier = match.group(1)


class InlineMacro(SpanToken):

    """Inline macro token.

    Examples:

        In a sentence @macroname it appears.
                      ^^^^^^^^^^

        In a sentence @macroname{argument} it appears.
                      ^^^^^^^^^^^^^^^^^^^^
    """

    pattern = re.compile(r"(?<!\\)@([a-z]+[a-z0-9]*)(?:{([^}]*)}|\b)")
    parse_inner = False

    def __init__(self, match):
        super().__init__(match)
        self.name = match.group(1)
        self.arg = match.group(2)


class BlockMacro(BlockToken):

    """Block macro token.

    Examples:

        @macroname

        @macroname{argument}

        @macroname:
        > This will be passed as children.

        @macroname{argument}:
        > This will be passed as children.

        @macroname
        > This is just a regular blockquote.

    It is invalid to invoke the macro with a colon without providing children
    (the blockquote). The renderer must check for this.
    """

    pattern = re.compile(r"^@([a-z]+[a-z0-9]*)(?:{([^}]*)})?(:)?$")

    name = ""
    arg = ""
    colon = ""

    def __init__(self, result):
        self.name, self.arg, self.colon, lines = result
        super().__init__(lines, block_token.tokenize)

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
        if cls.colon:
            for line in lines:
                if not Quote.start(line):
                    break
                line_buffer.append(line)
        return cls.name, cls.arg, cls.colon, line_buffer


class RenderOptions(NamedTuple):

    """Options for rendering ZFM."""

    shift_headings_by: int = 0


class ZFMRenderer(HTMLRenderer):

    """Renderer from ZFM to HTML."""

    def __init__(self, ctx: Context, options: RenderOptions):
        super().__init__(ExtendedHeading, BlockMacro, InlineMacro)
        ctx.renderer = self
        self.ctx = ctx
        self.options = options
        self.inline_code_macro = ctx.project.cfg["inline_code_macro"]
        self.smart_typography = ctx.project.cfg["smart_typography"]
        self.image_links = ctx.project.cfg["image_links"]

    def error(self, message: str) -> str:
        """Log an error and render it."""
        logging.error("%s: %s", self.ctx.article.path, message)
        return self.render_error(message)

    @staticmethod
    def render_error(message: str) -> str:
        return f'<span style="color: red; font-weight: bold">[{message}]</span>'

    def render(self, token: Token) -> str:
        error = getattr(token, "zfm_error", None)
        if error is not None:
            return self.render_error(error)
        return super().render(token)

    def run_macro(
        self, name: str, arg: str, block: Optional[List[BlockToken]], kind: Kind
    ) -> str:
        macro = self.ctx.project.get_macro(name)
        if not macro:
            return self.error(f"{name}: undefined macro")
        if macro.kind is not kind:
            actual = macro.kind.name.lower()
            called = kind.name.lower()
            return self.error(f"{name}: {actual} macro invoked as {called} macro")
        try:
            return macro(self.ctx, arg, block)
        except MacroError as ex:
            return self.error(f"{name}: {ex}")

    def render_inline_macro(self, token: InlineMacro) -> str:
        return self.run_macro(token.name, token.arg, None, Kind.INLINE)

    def render_inline_code(self, token: InlineCode) -> str:
        if self.inline_code_macro:
            text = token.children[0].content
            return self.run_macro(self.inline_code_macro, text, None, Kind.INLINE)
        return super().render_inline_code(token)

    def render_block_macro(self, token: BlockMacro) -> str:
        block = None
        if token.children:
            assert isinstance(token.children[0], Quote)
            block = token.children[0].children
        elif token.colon:
            return self.error(f"{token.name}: missing blockquote after colon")
        if token.name == "include":
            if token.children:
                return self.error("include: macro does not take blockquote")
            doc = token.zfm_include.doc
            return self.render_inner(doc)
        return self.run_macro(token.name, token.arg, block, Kind.BLOCK)

    def render_extended_heading(self, token: Heading) -> str:
        # TODO: Make this driven by the builder.
        template = '<a id="{id}" data-hs-anchor="true"></a><h{level}>{inner}</h{level}>'
        level = max(1, min(6, token.level + self.options.shift_headings_by))
        inner = self.render_inner(token)
        return template.format(level=level, id=token.identifier, inner=inner)

    def render_raw_text(self, token: RawText) -> str:
        if self.smart_typography:
            token.content = smartify(token.content)
        return super().render_raw_text(token)

    def render_link(self, token: Link) -> str:
        interlink = getattr(token, "zfm_interlink", None)
        if interlink:
            token.target = self.ctx.builder.resolve_link(self.ctx, interlink)
            if not token.children:
                token.children = [raw_text(interlink.article.title)]
        # Need noopener for TOC links to work in HubSpot. Otherwise it scrolls
        # past a bit. Good idea in general to use noopener.
        # TODO: Make this driven by the builder.
        template = '<a href="{target}"{title} rel="noopener">{inner}</a>'
        target = self.escape_url(token.target)
        if token.title:
            title = ' title="{}"'.format(self.escape_html(token.title))
        else:
            title = ''
        inner = self.render_inner(token)
        return template.format(target=target, title=title, inner=inner)

    def render_image(self, token: Image) -> str:
        if not getattr(token, "zfm_image_processed", False):
            token.zfm_image_processed = True
            asset = getattr(token, "zfm_asset", None)
            if asset:
                token.src = self.ctx.builder.resolve_asset(self.ctx, asset)
            if self.image_links:
                return super().render_link(link(token.src, [token]))
        return super().render_image(token)
