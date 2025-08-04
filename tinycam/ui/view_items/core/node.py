from collections.abc import Sequence
from typing import override

from tinycam.ui.view import ViewItem, Context, RenderState


class Node(ViewItem):
    def __init__(self, context: Context):
        super().__init__(context)

        self._parent = None
        self._children = []

    @property
    def parent(self) -> 'Node | None':
        return self._parent

    @parent.setter
    def parent(self, value: 'Node | None'):
        self._parent = value

    @property
    def children(self) -> 'Sequence[Node]':
        return self._children[:]

    def add_child(self, child: 'Node', update_parent: bool = True):
        if child in self._children:
            return

        self._children.append(child)
        if update_parent:
            child.parent = self

    def remove_child(self, child: 'Node', update_parent: bool = True):
        if child not in self._children:
            return

        self._children.remove(child)
        if update_parent:
            child.parent = None

    def has_child(self, child: 'Node') -> bool:
        return child in self._children

    def clear_children(self, update_parents: bool = True):
        if update_parents:
            for child in self._children:
                child.parent = None

        self._children.clear()

    @override
    def render(self, state: RenderState):
        for child in self.children:
            child.render(state)
