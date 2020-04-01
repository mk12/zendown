"""Zendown flavored Markdown. It extends Markdown with macros."""

import inspect
import logging
import re
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from mistletoe.block_token import BlockToken, Heading, Quote, tokenize
from mistletoe.span_token import Link, Image, InlineCode, SpanToken, RawText
from mistletoe.html_renderer import HTMLRenderer

from zendown.tokens import Token
from zendown.tree import COLLISION, Label, Ref

# Only import these for mypy.
if False:  # pylint: disable=using-constant-test
    # pylint: disable=unused-import,cyclic-import
    from zendown.article import Article
    from zendown.build import Builder
    from zendown.project import Project


def postprocess_heading(heading: Heading):
    """Perform extra ZFM tokenizing on a heading block.

    In particular, this sets the identifier field. For example:

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


# Allowed type signatures for macro functions.
MacroFunction = Union[
    Callable[[Context], str],
    Callable[[Context, str], str],
    Callable[[Context, List[BlockToken]], str],
    Callable[[Context, str, List[BlockToken]], str],
]


class MacroError(Exception):
    """An error that occurs during macro execution."""


class Macro:

    """ZFM macro.

    A macro is defined by a function that takes the following arguments:

        ctx: Context
            Required. The rendering context.

        arg: str
            Optional. The untokenized argument provided between braces. For
            example, @icon{gear} would has the arg "gear". Macros can choose to
            tokenize using zendown.tokens.tokenize if they wish.

            If the macro does not take this parameter, it is an error to provide
            an argument when invoking the macro in an article.

        children: List[BlockItem]
            Optional. The tokenized children provided in the blockquote
            following the colon. For example:

                @tip:
                > _This_ paragraph is `children[0]`.

            If the macro does not take this parameter, it is an error to provide
            a blockquote when invoking the macro in an article.

    The function must return a string of rendered HTML.
    """

    def __init__(self, function: MacroFunction):
        self.name = function.__name__
        self.function: Callable[..., str] = function
        parameters = inspect.signature(function).parameters
        self.requires_arg = "arg" in parameters
        self.requires_children = "children" in parameters

    def __call__(self, ctx: Context, arg: str, children: List[BlockToken]) -> str:
        arguments: Dict[str, Any] = {"ctx": ctx}
        if self.requires_arg:
            arguments["arg"] = arg
        elif arg:
            raise MacroError("macro does not take argument")
        if self.requires_children:
            arguments["children"] = children
        elif children:
            raise MacroError("macro does not take blockquote")
        return self.function(**arguments)


MT = TypeVar("MT", bound=MacroFunction)


def macro(f: MT) -> MT:
    """Mark a function as a macro.

    This doesn't change the function itself. It just injects a entry into the
    global _macros dictionary.
    """
    scope = getattr(f, "__globals__")
    if not "_macros" in scope:
        scope["_macros"] = {}
    scope["_macros"][f.__name__] = Macro(f)
    return f


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

    # TODO consider removing


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
        macro_obj = self.ctx.project.get_macro(name)
        if not macro_obj:
            return self.error("undefined macro", name)
        try:
            return macro_obj(self.ctx, arg, children)
        except MacroError as ex:
            return self.error("macro error", name, str(ex))

    def render_heading(self, token):
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
            article: Optional["Article"] = None
            if path.startswith("/"):
                ref: Ref["Article"] = Ref.parse(path)
                article = self.ctx.project.articles_by_ref.get(ref)
            elif "/" not in path:
                label: Label["Article"] = Label(path)
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
