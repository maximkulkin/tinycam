from collections.abc import Sequence

from tinycam.ui.view import Context
from tinycam.ui.view_items.core.node import Node
from tinycam.types import Vector2, Vector3, Quaternion, Matrix44


class Node2D(Node):
    def __init__(self, context: Context):
        super().__init__(context)

        self._position = Vector2(0, 0)
        self._rotation = Quaternion()
        self._scale = Vector2(1, 1)

        self._local_matrix = None
        self._world_matrix = None

    @property
    def parent(self) -> 'Node2D | None':
        return self._parent

    @parent.setter
    def parent(self, value: 'Node2D | None'):
        self._parent = value
        self._invalidate_world_matrix()

    @property
    def position(self) -> Vector2:
        return self._position

    @position.setter
    def position(self, value: Vector2):
        self._position = value
        self._invalidate_local_matrix()

    @property
    def rotation(self) -> Quaternion:
        return self._rotation

    @rotation.setter
    def rotation(self, value: Quaternion):
        self._rotation = value
        self._invalidate_local_matrix()

    @property
    def scale(self) -> Vector2:
        return self._scale

    @scale.setter
    def scale(self, value: Vector2):
        self._scale = value
        self._invalidate_local_matrix()

    @property
    def world_position(self) -> Vector2:
        return (self.parent.world_position if self.parent is not None else Vector2()) + self._position

    @world_position.setter
    def world_position(self, value: Vector2):
        parent_position = self.parent.world_position if self.parent is not None else Vector2()
        self._position = value - parent_position
        self._invalidate_local_matrix()

    @property
    def world_rotation(self) -> Quaternion:
        return (self.parent.world_rotation if self.parent is not None else Quaternion()) + self._rotation

    @world_rotation.setter
    def world_rotation(self, value: Quaternion):
        parent_rotation = self.parent.world_rotation if self.parent is not None else Quaternion()
        self._rotation = parent_rotation.conjugate * value
        self._invalidate_local_matrix()

    @property
    def world_scale(self) -> Vector2:
        return (self.parent.world_scale if self.parent is not None else Vector2(1, 1)) * self._scale

    @world_scale.setter
    def world_scale(self, value: Vector2):
        parent_scale = self.parent.world_scale if self.parent is not None else Vector2(1, 1)
        if parent_scale.x == 0:
            parent_scale.x = 1
        if parent_scale.y == 0:
            parent_scale.y = 1
        self._scale = value / parent_scale
        self._invalidate_local_matrix()

    @property
    def local_matrix(self) -> Matrix44:
        if self._local_matrix is None:
            self._local_matrix = (
                Matrix44.from_translation(Vector3.from_vector2(self._position)) *
                Matrix44.from_rotation(self._rotation) *
                Matrix44.from_scale(Vector3.from_vector2(self._scale, 1.0))
            )
        return self._local_matrix

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

    @property
    def children(self) -> 'Sequence[Node2D]':
        return super().children

    def add_child(self, child: 'Node2D', update_parent: bool = True):
        super().add_child(child, update_parent=update_parent)

    def remove_child(self, child: 'Node2D', update_parent: bool = True):
        super().remove_child(child, update_parent=update_parent)

    def has_child(self, child: 'Node2D') -> bool:
        return super().has_child(child)
