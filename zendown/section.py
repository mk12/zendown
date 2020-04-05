"""Zendown article section."""

from __future__ import annotations

from typing import Callable, Container, List, Optional, Set

from mistletoe.block_token import BlockToken, Heading

from zendown.tree import Label, Node, Tree


class Section:

    """A section within an article body.

    A section comprises a heading and a list of blocks. The heading can be any
    level (H1 to H6). The section stores blocks up until the next heading of
    equal or lower level (i.e. same or bigger font).

    This class is useful for manipulating article content, since the mistletoe
    tokenization is flat with respect to headings.
    """

    def __init__(self, heading: Heading, node: Node[Section]):
        self.heading = heading
        self.node = node
        self.blocks: List[BlockToken] = []


# Sections form a tree, but we refer to them by Label rather than Ref because
# they must have unique labels (since they are used for the HTML id attribute).
Anchor = Label[Section]


# A function that generates a label for a heading, given the set of used labels.
GenLabelFn = Callable[[Heading, Container[Anchor]], Anchor]


def parse_sections(
    tokens: List[BlockToken], gen_label: Optional[GenLabelFn] = None
) -> Tree[Section]:
    """Parse tokens into a tree of sections.

    If gen_label is provided, it will be used to generate labels in the tree.
    Otherwise, unspecified integers will be used.
    """
    if not gen_label:
        gen_label = lambda heading, used: Label(str(id(heading)))
    tree: Tree[Section] = Tree()
    parent = tree.root
    blocks = []
    node = None
    used: Set[Anchor] = set()
    for token in tokens:
        if not isinstance(token, Heading):
            blocks.append(token)
            continue
        if node:
            node.item.blocks = blocks
        blocks = []
        label = gen_label(token, used)
        used.add(label)
        if node and token.level > node.item.heading.level:
            parent = node
        else:
            while parent.item and token.level <= parent.item.heading.level:
                assert parent.parent
                parent = parent.parent
        node = parent.add_child(label)
        tree.register(node, Section(token, node))
    if node:
        assert node.item
        node.item.blocks = blocks

    # At this point, the Section objects only store the blocks up to the
    # next heading. Extend them to cover all the blocks in their subtree.
    def extend_blocks(node: Node[Section]) -> List[BlockToken]:
        assert node.item
        for child in node.children.values():
            node.item.blocks.extend(extend_blocks(child))
        return [node.item.heading] + node.item.blocks

    for node in tree.root.children.values():
        extend_blocks(node)
    return tree
