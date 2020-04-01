"""Tree structure for articles."""

import sys
from typing import Any, Dict, Generic, Iterator, Optional, TextIO, Tuple, TypeVar, Union


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


class Ref(Generic[T]):

    """A list of labels identifying a node in a tree."""

    def __init__(self, parts: Tuple[Label[T], ...]):
        self.parts = parts

    @staticmethod
    def parse(s: str) -> "Ref[T]":
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

ROOT: Label[Any] = Label("$root")


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

    def print_tree(self, out: TextIO = sys.stdout):
        """Print the tree rooted at this node."""

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
        return Node(ROOT)

    def set_item(self, item: T):
        self.item = item

    def add_child(self, child: "Node[T]"):
        self.children[child.label] = child
        child.parent = self

    def is_root(self) -> bool:
        return self.label is ROOT

    def set_refs_recursively(self):
        assert self.is_root()

        def go(node: Node[T]):
            for label, child in node.children.items():
                assert node.ref is not None
                child.ref = Ref(node.ref.parts + (label,))
                go(child)

        self.ref = Ref(())
        go(self)

    def traverse_nodes(self) -> Iterator["Node[T]"]:
        yield self
        for child in self.children.values():
            yield from child.traverse_nodes()

    def items_by_ref(self) -> Dict[Ref[T], T]:
        items = {}
        for node in self.traverse_nodes():
            if node.item is not None:
                assert node.ref
                items[node.ref] = node.item
        return items

    def items_by_label(self) -> Dict[Label[T], Union[T, Collision]]:
        items: Dict[Label[T], Union[T, Collision]] = {}
        for node in self.traverse_nodes():
            if node.item is not None:
                if node.label in items:
                    items[node.label] = COLLISION
                else:
                    items[node.label] = node.item
        return items
