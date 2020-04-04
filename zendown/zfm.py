"""Zendown flavored Markdown. It extends Markdown with macros."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, Optional, cast

from mistletoe import block_token, span_token
from mistletoe.block_token import BlockToken, Document, Heading, Quote, tokenize
from mistletoe.html_renderer import HTMLRenderer
from mistletoe.span_token import Image, InlineCode, Link, RawText, SpanToken

from zendown.macro import Context, Kind, MacroError
from zendown.tokens import link, raw_text, strip_comments
from zendown.tree import COLLISION, Label, Ref

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from zendown.article import Article


def parse_document(raw: str) -> Document:
    """Parse a ZFM document."""
    block_token.remove_token(Heading)
    block_token.add_token(ExtendedHeading)
    block_token.add_token(BlockMacro)
    span_token.add_token(InlineMacro)
    doc = Document(raw)
    strip_comments(doc)
    block_token.reset_tokens()
    span_token.reset_tokens()
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
        if cls.colon:
            for line in lines:
                if not Quote.start(line):
                    break
                line_buffer.append(line)
        return cls.name, cls.arg, cls.colon, line_buffer


class ZFMRenderer(HTMLRenderer):

    """Renderer from ZFM to HTML."""

    def __init__(self, ctx: Context):
        super().__init__()
        ctx.renderer = self
        self.ctx = ctx
        self.inline_code_macro = ctx.project.cfg["inline_code_macro"]
        self.smart_typography = ctx.project.cfg["smart_typography"]
        self.image_links = ctx.project.cfg["image_links"]
        self.render_map.update(
            {
                ExtendedHeading.__name__: self.render_extended_heading,
                InlineMacro.__name__: self.render_inline_macro,
                BlockMacro.__name__: self.render_block_macro,
            }
        )

    def error(self, message: str) -> str:
        logging.error("%s: %s", self.ctx.article.path, message)
        return f'<span style="color: red; font-weight: bold">[{message}]</span>'

    def run_macro(self, name: str, arg: str, children: Any, kind: Kind) -> str:
        macro = self.ctx.project.get_macro(name)
        if not macro:
            return self.error(f"{name}: undefined macro")
        if macro.kind is not kind:
            actual = macro.kind.name.lower()
            called = kind.name.lower()
            return self.error(f"{name}: {actual} macro invoked as {called} macro")
        try:
            return macro(self.ctx, arg, children)
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
        children = None
        if token.children:
            assert isinstance(token.children[0], Quote)
            children = token.children[0].children
        elif token.colon:
            return self.error(f"{token.name}: missing blockquote after colon")
        return self.run_macro(token.name, token.arg, children, Kind.BLOCK)

    def render_extended_heading(self, token: Heading) -> str:
        template = '<h{level} id="{id}">{inner}</h{level}>'
        inner = self.render_inner(token)
        return template.format(level=token.level, id=token.identifier, inner=inner)

    def render_raw_text(self, token: RawText) -> str:
        if self.smart_typography:
            token.content = smartify(token.content)
        return super().render_raw_text(token)

    def render_link(self, token: Link) -> str:
        if not token.target:
            return self.error("invalid empty link")
        if "." not in token.target:
            path, anchor = token.target, ""
            if "#" in path:
                path, anchor = path.split("#", 1)
            article: Optional[Article] = None
            if path == "":
                article = self.ctx.article
            elif path.startswith("/"):
                ref: Ref[Article] = Ref.parse(path)
                article = self.ctx.project.articles_by_ref.get(ref)
            elif "/" not in path:
                label: Label[Article] = Label(path)
                maybe_article = self.ctx.project.articles_by_label.get(label)
                if maybe_article is COLLISION:
                    return self.error(f"ambiguous article name {path!r}")
                article = cast(Optional["Article"], maybe_article)
            if article is None:
                return self.error(f"invalid article link {token.target!r}")
            url = self.ctx.builder.resolve_article(self.ctx, article)
            if anchor:
                if article.anchors.get(Label(anchor)) is None:
                    return self.error(
                        f"article {article.node.ref!r} has no anchor {anchor!r}"
                    )
                url += "#" + anchor
            token.target = url
            if not token.children:
                article.ensure_loaded()
                assert article.cfg
                token.children = [raw_text(article.cfg["title"])]
        return super().render_link(token)

    def render_image(self, token: Image) -> str:
        if not getattr(token, "zfm_image_processed", False):
            token.zfm_image_processed = True
            if not (
                token.src.startswith("http://") or token.src.startswith("https://")
            ):
                token.src = self.ctx.builder.resolve_asset(self.ctx, token.src)
            if self.image_links:
                return super().render_link(link(token.src, [token]))
        return super().render_image(token)
