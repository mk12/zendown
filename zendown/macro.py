"""Zendown macros."""

from __future__ import annotations

import enum
import inspect
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, TypeVar, Union

from mistletoe.block_token import BlockToken

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
    Callable[[Context], str], Callable[[Context, str], str],
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
        scope["_macros"] = {kind: {} for kind in Kind}
    scope["_macros"][f.__name__] = Macro(f, Kind.INLINE)
    return f


def block_macro(f: BMF) -> BMF:
    """Decorator that marks a function as a block macro."""
    scope = getattr(f, "__globals__")
    if not "_macros" in scope:
        scope["_macros"] = {kind: {} for kind in Kind}
    scope["_macros"][f.__name__] = Macro(f, Kind.BLOCK)
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

    def __init__(self, function: MacroFunction, kind: Kind):
        self.name = function.__name__
        self.function: Callable[..., str] = function
        self.kind = kind
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
