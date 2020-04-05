"""Generic tree structure."""

from __future__ import annotations

import sys
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    Optional,
    TextIO,
    Tuple,
    TypeVar,
    Union,
    cast,
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

    def __init__(self, label: Label[T], ref: Ref[T], parent: Optional[Node[T]]):
        self.label = label
        self.ref = ref
        self.parent: Optional[Node[T]] = parent
        self.item: Optional[T] = None
        self.children: Dict[Label[T], Node[T]] = {}

    def __repr__(self) -> str:
        return f"Node(label={self.label!r}, ref={self.ref!r}, item={self.item!r})"

    @staticmethod
    def root():
        """Return the root node. All trees should use this as their root."""
        return Node(ROOT, Ref(()), None)

    def set_item(self, item: T):
        """Set the node's item."""
        self.item = item

    def add_child(self, label: Label[T]) -> Node[T]:
        """Add a child with the given label."""
        child = Node(label, Ref(self.ref.parts + (label,)), self)
        self.children[label] = child
        return child


class Tree(Generic[T]):

    """A tree of nodes associated with items of type T."""

    def __init__(self):
        self.root = Node.root()
        self.by_ref: Dict[Ref[T], T] = {}
        self.by_label: Dict[Label[T], Union[T, Collision]] = {}

    def __repr__(self) -> str:
        refs = ", ".join(str(r) for r in self.by_ref)
        return f"Tree(refs=[{refs}])"

    def dump(self, out: TextIO = sys.stdout):
        """Dump a textual representation of the tree to out."""

        def go(node: Node[T], indent: int):
            space = "    " * indent
            item = ""
            if node.item is not None:
                item = f" = {node.item!r}"
            print(f"{space}{node.label}{item}", file=out)
            for child in node.children.values():
                go(child, indent + 1)

        go(self.root, 0)

    def create(self, ref: Ref[T], make_item: Callable[..., T], *args, **kwargs) -> T:
        """Create a new node and item.

        Places the node in the tree using ref, creating intermediate nodes as
        necessary. Creates the node's item by calling make_item with the extra
        arguments and the new node. Returns the new item.
        """
        node = self.root
        for label in ref.parts:
            if label in node.children:
                node = node.children[label]
            else:
                node = node.add_child(label)
        item = make_item(*args, **kwargs, node=node)
        self.register(node, item)
        return item

    def register(self, node: Node[T], item: T):
        """Set the node's item and register the item in by_ref and by_label."""
        node.set_item(item)
        self.by_ref[node.ref] = item
        label = node.ref.parts[-1]
        if label in self.by_label:
            self.by_label[label] = COLLISION
        else:
            self.by_label[label] = item

    @property
    def by_unique_label(self) -> Dict[Label[T], T]:
        """Like by_label, but asserting that there are no collisions."""
        return cast(Dict[Label[T], T], self.by_label)

    def __iter__(self) -> Iterator[T]:
        """Iterate over all items."""
        return iter(self.by_ref.values())

    def first_level(self) -> Iterator[T]:
        """Iterate over the items in the first level of the tree."""
        for child in self.root.children:
            if child.item is not None:
                yield child.item
