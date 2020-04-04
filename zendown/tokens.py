"""Helpers for building and manipulating mistletoe tokens."""

from typing import Callable, List, Union

from mistletoe import block_token, span_token
from mistletoe.block_token import BlockToken, HTMLBlock, ListItem, Paragraph
from mistletoe.span_token import Emphasis, HTMLSpan, Link, RawText, SpanToken, Strong

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


def strip_comments(token: Token):
    """Remove all HTML comment tokens."""

    def is_comment(t: Token) -> bool:
        return isinstance(t, (HTMLBlock, HTMLSpan)) and t.content.startswith("<!--")

    def go(t: Token):
        if hasattr(t, "children"):
            t.children = [child for child in t.children if not is_comment(child)]

    walk(token, go)


def transform_text(tokens: List[Token], f: Callable[[str], str]):
    """Transform tokens by applying f to all raw text."""

    def go(t: Token):
        if isinstance(t, RawText):
            t.content = f(t.content)

    walk(tokens, go)


def collect_text(token: Token) -> str:
    """Return all raw text in token concatenated together."""
    text = ""

    def go(token: Token):
        if isinstance(token, RawText):
            nonlocal text
            text += token.content

    walk(token, go)
    return text


def raw_text(text: str) -> RawText:
    """Create a RawText token."""
    return RawText(text)


def strong(children: List[SpanToken]) -> Strong:
    """Create a Strong token."""
    token = Strong(None)
    token.children = children
    return token


def emphasis(children: List[SpanToken]) -> Emphasis:
    """Create an Emphasis token"""
    token = Emphasis(None)
    token.children = children
    return token


def link(target: str, children: List[SpanToken], title: str = "") -> Link:
    """Create a Link token."""
    token = Link.__new__(Link)
    token.target = target
    token.children = children
    token.title = title
    return token


def paragraph(children: List[SpanToken]) -> Paragraph:
    """Create a Paragraph token."""
    token = Paragraph.__new__(Paragraph, [])  # pylint: disable=too-many-function-args
    token.children = children
    return token


def bullet_list(
    children: List[List[BlockToken]], loose: bool = False
) -> block_token.List:
    """Create a List token with bulleted items."""
    return list_token(children, ordered=False, loose=loose)


def ordered_list(
    children: List[List[BlockToken]], loose: bool = False
) -> block_token.List:
    """Create a List token with ordered items."""
    return list_token(children, ordered=True, loose=loose)


def list_token(
    children: List[List[BlockToken]], ordered: bool, loose: bool,
) -> block_token.List:
    def make_item(tokens: List[BlockToken]) -> ListItem:
        item = ListItem.__new__(ListItem)
        item.leader = "-"
        item.prepend = 2
        item.loose = loose
        item.children = tokens
        return item

    token = block_token.List.__new__(block_token.List)
    token.loose = loose
    token.start = 1 if ordered else None
    token.children = [make_item(tokens) for tokens in children]
    return token
