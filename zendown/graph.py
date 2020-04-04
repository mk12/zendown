"""Generic directed graph structure."""

from __future__ import annotations

import sys
from typing import Generic, TextIO, TypeVar


T = TypeVar("T")


class Graph(Generic[T]):

    """A directed graph.

    Vertices are objects of type T.
    """

    def __init__(self):
        self.adjacency = {}

    def __repr__(self):
        return f"Graph(N={len(self.adjacency)})"

    def dump(self, out: TextIO = sys.stdout):
        """Dump a textual representation of this graph to out."""
        pass

    def add_vertex(self, vertex: T):
        self.adjacency[vertex] = set()

    def add_edge(self, src: T, dst: T):
        self.adjacency[src].add(dst)
    