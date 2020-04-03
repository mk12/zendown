"""Zendown article section."""

from __future__ import annotations

from typing import Callable, Container, List, Optional, Set

from mistletoe.block_token import BlockToken, Heading

from zendown.tree import Label, Node


class Section:

    """A section within an article body.

    A section comprises a heading and a list of blocks. The heading can be any
    level (H1 to H6). The section stores blocks up until the next heading of
    equal or lower level (i.e. same or bigger font).

    This class is useful for manipulating article content, since the mistletoe
    tokenization is flat with respect to headings.
    """

    def __init__(self, node: Node[Section], heading: Heading):
        self.node = node
        self.heading = heading
        self.blocks: List[BlockToken] = []


# A function that generates a label for a heading, given the set of used labels.
GenLabelFn = Callable[[Heading, Container[Label[Section]]], Label[Section]]


def parse_sections(
    tokens: List[BlockToken], gen_label: Optional[GenLabelFn] = None
) -> Node[Section]:
    """Parse tokens into a tree of sections.

    If gen_label is provided, it will be used to generate labels in the tree.
    Otherwise, unspecified integers will be used.
    """
    if not gen_label:
        gen_label = lambda heading, used: Label(str(id(heading)))
    tree: Node[Section] = Node.root()
    parent = tree
    blocks = []
    prev = None
    used: Set[Label[Section]] = set()
    for token in tokens:
        if not isinstance(token, Heading):
            blocks.append(token)
            continue
        if prev:
            prev.item.blocks = blocks
        blocks = []
        label = gen_label(token, used)
        node = Node(label)
        section = Section(node, token)
        node.set_item(section)
        used.add(label)
        if prev and token.level > prev.item.heading.level:
            parent = prev
        else:
            while parent.item and token.level <= parent.item.heading.level:
                assert parent.parent
                parent = parent.parent
        parent.add_child(node)
        prev = node
    if prev:
        assert prev.item
        prev.item.blocks = blocks

    # At this point, the Section objects only store the blocks up to the
    # next heading. Extend them to cover all the blocks in their subtree.
    def extend_blocks(node: Node[Section]) -> List[BlockToken]:
        assert node.item
        for child in node.children.values():
            node.item.blocks.extend(extend_blocks(child))
        return [node.item.heading] + node.item.blocks

    for node in tree.children.values():
        extend_blocks(node)
    tree.set_refs_recursively()
    return tree
