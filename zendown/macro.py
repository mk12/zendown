"""Zendown macros."""

from __future__ import annotations

import enum
import inspect
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, TypeVar, Union

from mistletoe.block_token import BlockToken
from mistletoe.span_token import SpanToken, tokenize_inner

from zendown.tokens import Token

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from zendown.article import Article
    from zendown.build import Builder
    from zendown.project import Project
    from zendown.zfm import ZFMRenderer


class Context:

    """Context passed to macros.

    Macros are meant to have access to absolutely everything.
    """

    def __init__(self, builder: Builder, project: Project, article: Article):
        self.builder = builder
        self.project = project
        self.article = article
        # This is set in ZFMRenderer.__init__.
        self.renderer: Optional[ZFMRenderer] = None

    def render(self, token: Union[Token, List[Token]]) -> str:
        """Render a token or a list of tokens to HTML."""
        assert self.renderer
        if not isinstance(token, list):
            return self.renderer.render(token)
        if any(isinstance(c, BlockToken) for c in token):
            return "\n".join(self.renderer.render(c) for c in token)
        return "".join(self.renderer.render(c) for c in token)


class Kind(enum.Enum):
    """Kinds of macros."""

    INLINE = enum.auto()
    BLOCK = enum.auto()


# Allowed type signatures for macro functions.
InlineMacroFunction = Union[
    Callable[[Context], str],
    Callable[[Context, str], str],
    Callable[[Context, List[SpanToken]], str],
]
BlockMacroFunction = Union[
    Callable[[Context], str],
    Callable[[Context, str], str],
    Callable[[Context, List[BlockToken]], str],
    Callable[[Context, str, List[BlockToken]], str],
]
MacroFunction = Union[
    InlineMacroFunction, BlockMacroFunction,
]

IMF = TypeVar("IMF", bound=InlineMacroFunction)
BMF = TypeVar("BMF", bound=BlockMacroFunction)


def inline_macro(f: IMF) -> IMF:
    """Decorator that marks a function as an inline macro."""
    scope = getattr(f, "__globals__")
    if not "_macros" in scope:
        scope["_macros"] = {}
    scope["_macros"][f.__name__] = Macro(Kind.INLINE, f)
    return f


def block_macro(f: BMF) -> BMF:
    """Decorator that marks a function as a block macro."""
    scope = getattr(f, "__globals__")
    if not "_macros" in scope:
        scope["_macros"] = {}
    scope["_macros"][f.__name__] = Macro(Kind.BLOCK, f)
    return f


class MacroError(Exception):
    """An error that occurs during macro execution."""


class Macro:

    """ZFM macro.

    A macro is defined by a function that takes the following arguments:

        ctx: Context
            Required. The rendering context.

        arg: str
            Optional. The untokenized argument provided between braces. For
            example, @icon{gear} would has the arg "gear".

        children: List[SpanItem]
            Optional (inline macros only). The tokenized children provided
            between braces. Inline macros must take arg or children, not both.
            Example:

                @stylize{_This emphasis is `children[0]`_}.

        children: List[BlockItem]
            Optional (block macros only). The tokenized children provided in the
            blockquote following the colon. Block macros can take both arg and
            children (or one, or neither). Example:

                @tip:
                > _This_ paragraph is `children[0]`.

    The function must return a string of rendered HTML. The ctx.render function
    is helpful for this.
    """

    def __init__(self, kind: Kind, function: MacroFunction):
        self.kind = kind
        self.name = function.__name__
        self.function: Callable[..., str] = function
        parameters = inspect.signature(function).parameters
        self.requires_arg = "arg" in parameters
        self.requires_children = "children" in parameters
        if self.requires_arg:
            ann = parameters["arg"].annotation
            if ann and ann is not str:
                logging.error("%s: macro arg should be str, not %s", self.name, ann)
        if self.requires_children:
            ann = parameters["children"].annotation
            if kind is Kind.INLINE and ann and ann is not List[SpanToken]:
                logging.error("%s: expected List[SpanToken], not %s", self.name, ann)
            if kind is Kind.BLOCK and ann and ann is not List[BlockToken]:
                logging.error("%s: expected List[BlockToken], not %s", self.name, ann)
        if kind is Kind.INLINE and self.requires_arg and self.requires_children:
            logging.error("%s: inline macros take arg OR children", self.name)

    def __call__(
        self, ctx: Context, arg: str, block: Optional[List[BlockToken]]
    ) -> str:
        arguments: Dict[str, Any] = {"ctx": ctx}
        children: Optional[List[Token]] = block
        if self.kind is Kind.INLINE and self.requires_children:
            # Note: macros are executed in a rendering context, so
            # tokenize_inner will have access to all the extra tokens.
            children = tokenize_inner(arg)
            arg = ""
        if self.requires_arg:
            arguments["arg"] = arg
        elif arg:
            raise MacroError(f"unexpected argument {arg!r}")
        if self.requires_children:
            if children is None:
                # This can only happen for block macros. For inline macros, we'd
                # at least tokenize "" which becomes [].
                assert self.kind is Kind.BLOCK
                raise MacroError("macro needs a blockquote")
            arguments["children"] = children
        elif children:
            assert self.kind is Kind.BLOCK
            raise MacroError("macro does not take blockquote")
        return self.function(**arguments)
