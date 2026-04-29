from collections.abc import Sequence
from typing import cast

from tinycam.ui.view import Context
from tinycam.ui.view_items.core.node import Node
from tinycam.math_types import Vector2, Vector3, Quaternion, Matrix44


class Node2D(Node):
    def __init__(
        self,
        context: Context,
        *,
        position: Vector2 = Vector2(),
        rotation: float = 0.0,
        scale: Vector2 = Vector2(1, 1),
    ):
        super().__init__(context)

        self._position = position
        self._rotation = rotation
        self._scale = scale

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
    def rotation(self) -> float:
        return self._rotation

    @rotation.setter
    def rotation(self, value: float):
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
        parent_position = self.parent.world_position if self.parent is not None else Vector2()
        return self.position + parent_position

    @world_position.setter
    def world_position(self, value: Vector2):
        parent_position = self.parent.world_position if self.parent is not None else Vector2()
        self.position = value - parent_position

    @property
    def world_rotation(self) -> float:
        parent_rotation = self.parent.world_rotation if self.parent is not None else 0.0
        return parent_rotation + self._rotation

    @world_rotation.setter
    def world_rotation(self, value: float):
        parent_rotation = self.parent.world_rotation if self.parent is not None else 0.0
        self.rotation = value - parent_rotation

    @property
    def world_scale(self) -> Vector2:
        parent_scale = self.parent.world_scale if self.parent is not None else Vector2(1, 1)
        return parent_scale * self._scale

    @world_scale.setter
    def world_scale(self, value: Vector2):
        parent_scale = self.parent.world_scale if self.parent is not None else Vector2(1, 1)
        if parent_scale.x == 0:
            parent_scale.x = 1
        if parent_scale.y == 0:
            parent_scale.y = 1
        self.scale = value / parent_scale

    def _calculate_local_matrix(self) -> Matrix44:
        return (
            Matrix44.from_translation(Vector3.from_vector2(self.position)) *
            Matrix44.from_rotation(Quaternion.from_z_rotation(self.rotation)) *
            Matrix44.from_scale(Vector3.from_vector2(self.scale, 1.0))
        )

    @property
    def children(self) -> 'Sequence[Node2D]':
        return cast(Sequence[Node2D], super().children)

    def add_child(self, child: 'Node2D', update_parent: bool = True):
        super().add_child(child, update_parent=update_parent)

    def remove_child(self, child: 'Node2D', update_parent: bool = True):
        super().remove_child(child, update_parent=update_parent)

    def has_child(self, child: 'Node2D') -> bool:
        return super().has_child(child)
