"""Built-in Zendown macros."""

from typing import List

from mistletoe.block_token import BlockToken

from zendown.macro import Context, block_macro


@block_macro
def include(ctx: Context, arg: str, children: List[BlockToken]) -> str:
    return ""
