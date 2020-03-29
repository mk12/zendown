"""Tree structure for articles."""

from typing import Dict, Generic, Iterator, Optional, Tuple, TypeVar


class Label:

    """A label for a node in a tree."""

    def __init__(self, val: str):
        self.val = val

    def __str__(self) -> str:
        return self.val


class Ref:

    """A list of labels identifying a node in a tree."""

    def __init__(self, parts: Tuple[Label, ...]):
        self.parts = parts

    @staticmethod
    def parse(s: str) -> "Ref":
        assert len(s) >= 1 and s[0] == "/"
        return Ref(tuple(Label(p) for p in s[1:].split("/")))

    def __str__(self) -> str:
        return "/" + "/".join(str(label) for label in self.parts)


class Collision:
    """Type used for indicating Label collisions."""


COLLISION = Collision()

ROOT = Label("$root")

T = TypeVar("T")


class Node(Generic[T]):

    """A node in a tree.

    There are two kinds of nodes: items and dirs. Items have the item property
    set, and do not have children. Dirs do not have the item property set, and
    they may (but do not need to) have children.
    """

    def __init__(self, label: Label):
        self.label = label
        self.parent: Optional[Node] = None
        self.ref: Optional[Ref] = None
        self.item: Optional[T] = None
        self.children: Dict[Label, Node] = {}

    @staticmethod
    def root():
        return Node(ROOT)

    def set_item(self, item: T):
        assert not self.children
        self.item = item

    def add_child(self, child: "Node"):
        assert not self.item
        self.children[child.label] = child
        child.parent = self

    def is_item(self) -> bool:
        return bool(self.item)

    def is_dir(self) -> bool:
        return not self.is_item()

    def is_root(self) -> bool:
        return self.label is ROOT

    def set_refs_recursively(self):
        assert self.is_root()

        def go(node: Node):
            for label, child in node.children.items():
                assert node.ref is not None
                child.ref = Ref(node.ref.parts + (label,))
                go(child)

        self.ref = Ref(())
        go(self)

    def items(self) -> Iterator[T]:
        assert self.is_dir()
        for node in self.children.values():
            if node.item:
                yield node.item

    def dirs(self) -> Iterator["Node"]:
        assert self.is_dir()
        for node in self.children.values():
            if not node.item:
                yield node

    def all_items_recursively(self) -> Iterator[T]:
        if self.item:
            yield self.item
        for child in self.children.values():
            yield from child.all_items_recursively()
