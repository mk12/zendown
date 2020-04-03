"""Generic tree structure."""

from __future__ import annotations

import sys
from typing import (
    Any,
    Dict,
    Generic,
    Iterator,
    Optional,
    TextIO,
    Tuple,
    TypeVar,
    Union,
)


T = TypeVar("T")


class Label(Generic[T]):

    """A label for a node in a tree."""

    def __init__(self, val: str):
        self.val = val

    def __repr__(self) -> str:
        return self.val

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Label):
            return NotImplemented
        return self.val == other.val

    def __hash__(self) -> int:
        return hash(self.val)


ROOT: Label[Any] = Label("$root")


class Ref(Generic[T]):

    """A list of labels identifying a node in a tree.

    The ref does not include the special root label.
    """

    def __init__(self, parts: Tuple[Label[T], ...]):
        self.parts = parts

    @staticmethod
    def parse(s: str) -> Ref[T]:
        assert len(s) >= 1 and s[0] == "/"
        return Ref(tuple(Label(p) for p in s[1:].split("/")))

    def __repr__(self) -> str:
        return "/" + "/".join(str(label) for label in self.parts)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Ref):
            return NotImplemented
        return self.parts == other.parts

    def __hash__(self) -> int:
        return hash(self.parts)


class Collision:
    """Type used for indicating Label collisions."""


COLLISION = Collision()


class Node(Generic[T]):

    """A node in a tree.

    Each node can optionally have an item of type T associated with it. Nodes
    can have any number of children.
    """

    def __init__(self, label: Label[T]):
        self.label = label
        self.parent: Optional[Node[T]] = None
        self.ref: Optional[Ref[T]] = None
        self.item: Optional[T] = None
        self.children: Dict[Label[T], Node[T]] = {}

    def __repr__(self) -> str:
        return f"Node(label={self.label!r}, ref={self.ref!r}, item={self.item!r})"

    def dump(self, out: TextIO = sys.stdout):
        """Dump a textual representation of this tree to out."""

        def go(node: Node[T], indent: int):
            space = "    " * indent
            item = ""
            if node.item:
                item = f" = {node.item!r}"
            print(f"{space}{node.label}{item}", file=out)
            for child in node.children.values():
                go(child, indent + 1)

        go(self, 0)

    @staticmethod
    def root():
        """Return the root node. All trees should use this as their root."""
        return Node(ROOT)

    def is_root(self) -> bool:
        """Return true if this node is the root of the tree."""
        return self.label is ROOT

    def set_item(self, item: T):
        """Set this node's item."""
        self.item = item

    def add_child(self, child: Node[T]):
        """Add a child to this node."""
        self.children[child.label] = child
        child.parent = self

    def set_refs_recursively(self):
        """Set all refs in the tree.

        This should be called at the end of constructing a tree.
        """
        assert self.is_root()

        def go(node: Node[T]):
            for label, child in node.children.items():
                assert node.ref is not None
                child.ref = Ref(node.ref.parts + (label,))
                go(child)

        self.ref = Ref(())
        go(self)

    def items_of_children(self) -> Iterator[T]:
        """Yield items of the children of this node."""
        for child in self.children.values():
            if child.item:
                yield child.item

    def traverse_nodes(self) -> Iterator[Node[T]]:
        """Yield all nodes in the tree rooted at this node."""
        yield self
        for child in self.children.values():
            yield from child.traverse_nodes()

    def items_by_ref(self) -> Dict[Ref[T], T]:
        """Return a map from refs to nodes in this tree."""
        items = {}
        for node in self.traverse_nodes():
            if node.item is not None:
                assert node.ref
                items[node.ref] = node.item
        return items

    def items_by_label(self) -> Dict[Label[T], Union[T, Collision]]:
        """Return a map from labels to nodes in this tree.

        Labels that are ambiguous (multiple nodes in the tree have that label)
        are instead mapped to the special value COLLISION.
        """
        items: Dict[Label[T], Union[T, Collision]] = {}
        for node in self.traverse_nodes():
            if node.item is not None:
                if node.label in items:
                    items[node.label] = COLLISION
                else:
                    items[node.label] = node.item
        return items
