"""Example Zendown macros."""

from typing import List

from mistletoe.block_token import BlockToken, Paragraph

from zendown.macro import Context, block_macro, inline_macro
from zendown.section import parse_sections
from zendown.tokens import (
    bullet_list,
    link,
    paragraph,
    raw_text,
    strong,
    tokenize,
    transform_text,
)


@inline_macro
def yell(ctx: Context, arg: str) -> str:
    tokens = tokenize(arg)
    transform_text(tokens, str.upper)
    return ctx.render(tokens)


@inline_macro
def pop(ctx: Context, arg: str) -> str:
    return ctx.render(strong(tokenize(arg)))


@block_macro
def callout(ctx: Context, arg: str, children: List[BlockToken]) -> str:
    return f'<div class="{arg}">\n{ctx.render(children)}\n</div>'


@block_macro
def note(ctx: Context, children: List[BlockToken]) -> str:
    return callout(ctx, "note", children)


@block_macro
def warning(ctx: Context, children: List[BlockToken]) -> str:
    return callout(ctx, "warning", children)


@block_macro
def defs(ctx: Context, children: List[BlockToken]) -> str:
    result = []
    for section in parse_sections(children).items_of_children():
        label = strong(section.heading.children)
        blocks = section.blocks[:]
        if len(blocks) >= 1 and isinstance(blocks[0], Paragraph):
            blocks[0].children[0:0] = [label, raw_text(": ")]
        else:
            result.append(paragraph([label, raw_text(":")]))
        result.extend(blocks)
    return ctx.render(result)


@block_macro
def toc(ctx: Context) -> str:
    items = []
    for section in ctx.article.tree.items_of_children():
        anchor_link = link(f"#{section.heading.identifier}", section.heading.children)
        items.append([paragraph([anchor_link])])
    result = [paragraph([raw_text("In this article:")]), bullet_list(items)]
    return ctx.render(result)