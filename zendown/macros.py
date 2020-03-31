"""Example Zendown macros."""

from typing import List, Tuple

from zendown.zfm import Context, macro
from zendown.tokens import (
    BlockToken,
    Heading,
    Paragraph,
    RawText,
    Token,
    paragraph,
    raw_text,
    strong,
    tokenize,
    walk,
)


@macro
def upper(ctx: Context, arg: str) -> str:
    def transform(token: Token):
        if isinstance(token, RawText):
            token.content = token.content.upper()

    tokens = tokenize(arg)
    walk(tokens, transform)
    return ctx.render(tokens)


@macro
def callout(ctx: Context, arg: str, children: List[BlockToken]) -> str:
    return f'<div class="{arg}">\n{ctx.render(children)}\n</div>'


@macro
def note(ctx: Context, children: List[BlockToken]) -> str:
    return callout(ctx, "note", children)


@macro
def warning(ctx: Context, children: List[BlockToken]) -> str:
    return callout(ctx, "warning", children)


@macro
def defs(ctx: Context, children: List[BlockToken]) -> str:
    items: List[Tuple[BlockToken, List[BlockToken]]] = []
    for child in children:
        if isinstance(child, Heading) and child.level == 1:
            items.append((child, []))
        else:
            items[-1][1].append(child)
    all_blocks = []
    for term, blocks in items:
        label = strong(term.children)
        if len(blocks) >= 1 and isinstance(blocks[0], Paragraph):
            first = blocks.pop(0)
            first.children[0:0] = [label, raw_text(": ")]
        else:
            first = paragraph([label, raw_text(":")])
        all_blocks.append(first)
        all_blocks.extend(blocks)
    return ctx.render(all_blocks)


@macro
def toc(ctx: Context) -> str:
    lines = ["In this article:\n", "\n"]
    for token in ctx.article.doc.children:
        if isinstance(token, Heading) and token.level == 1:
            title = ctx.render(token.children)
            # TODO: using real thing
            lines.append(f"- [{title}](#{id})\n")
    return ctx.render(tokenize(lines))
