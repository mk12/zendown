"""Helpers for building mistletoe tokens."""

from typing import Callable, List, Union

from mistletoe import block_token, span_token
from mistletoe.block_token import (  # pylint: disable=unused-import
    BlockToken,
    BlockCode,
    Heading,
    Quote,
    CodeFence,
    ThematicBreak,
    List as ListToken,
    ListItem,
    Table,
    Footnote,
    Paragraph,
)
from mistletoe.span_token import (  # pylint: disable=unused-import
    EscapeSequence,
    Strikethrough,
    AutoLink,
    CoreTokens,
    InlineCode,
    LineBreak,
    RawText,
    SpanToken,
    Strong,
    Emphasis,
)


Token = Union[SpanToken, BlockToken]


def tokenize(raw: Union[str, List[str]]) -> List[Token]:
    """Tokenize raw input.

    If raw is a list of lines, it tokenizes at the block level. Otherwise (raw
    is a string), it tokenizes at the span level.
    """
    if isinstance(raw, list):
        return block_token.tokenize(raw)
    return span_token.tokenize_inner(raw)


def walk(tokens: Union[Token, List[Token]], f: Callable[[Token], None]):
    """Recursively call f on tokens and all descendants."""

    def go(t: Token):
        f(t)
        if hasattr(t, "children"):
            for child in t.children:
                go(child)

    if isinstance(tokens, list):
        for token in tokens:
            go(token)
    else:
        go(tokens)


def raw_text(text: str) -> RawText:
    """Create a RawText token."""
    return RawText(text)


def strong(children: List[SpanToken]) -> Strong:
    """Create a Strong token with children."""
    token = Strong(None)
    token.children = children
    return token


def paragraph(children: List[SpanToken]) -> Paragraph:
    """Create a paragraph token with children."""
    token = Paragraph.__new__(Paragraph, [])  # pylint: disable=too-many-function-args
    token.children = children
    return token
