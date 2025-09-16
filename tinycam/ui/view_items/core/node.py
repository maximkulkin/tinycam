from collections.abc import Sequence
from typing import override

from tinycam.types import Matrix44
from tinycam.ui.view import ViewItem, Context, RenderState


class Node(ViewItem):
    def __init__(self, context: Context):
        super().__init__(context)

        self._parent = None
        self._children = []
        self._visible = True

        self._local_matrix = None
        self._world_matrix = None

    @property
    def parent(self) -> 'Node | None':
        return self._parent

    @parent.setter
    def parent(self, value: 'Node | None'):
        self._parent = value

    @property
    def local_matrix(self) -> Matrix44:
        if self._local_matrix is None:
            self._local_matrix = self._calculate_local_matrix()

        return self._local_matrix

    def _calculate_local_matrix(self) -> Matrix44:
        return Matrix44.identity()

    @property
    def world_matrix(self) -> Matrix44:
        if self._world_matrix is None:
            parent_matrix = self.parent.world_matrix if self.parent is not None else Matrix44.identity()
            self._world_matrix = parent_matrix * self.local_matrix

        return self._world_matrix

    def _invalidate_local_matrix(self):
        self._local_matrix = None
        self._invalidate_world_matrix()

    def _invalidate_world_matrix(self):
        self._world_matrix = None
        for child in self.children:
            child._invalidate_world_matrix()

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

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        self._visible = value

    @override
    def render(self, state: RenderState):
        for child in self.children:
            child.render(state)
