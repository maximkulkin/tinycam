from collections.abc import Sequence
from typing import cast

from tinycam.types import Vector3, Quaternion, Matrix44
from tinycam.ui.view import Context
from tinycam.ui.view_items.core.node import Node


class Node3D(Node):
    def __init__(
        self,
        context: Context,
        *,
        position: Vector3 = Vector3(),
        rotation: Quaternion = Quaternion(),
        scale: Vector3 = Vector3(1, 1, 1),
    ):
        super().__init__(context)

        self._position = position
        self._rotation = rotation
        self._scale = scale

        self._local_matrix = None
        self._world_matrix = None

    @property
    def parent(self) -> 'Node3D | None':
        return self._parent

    @parent.setter
    def parent(self, value: 'Node3D | None'):
        self._parent = value
        self._invalidate_world_matrix()

    @property
    def position(self) -> Vector3:
        return self._position

    @position.setter
    def position(self, value: Vector3):
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
    def scale(self) -> Vector3:
        return self._scale

    @scale.setter
    def scale(self, value: Vector3):
        self._scale = value
        self._invalidate_local_matrix()

    @property
    def world_position(self) -> Vector3:
        parent_position = self.parent.world_position if self.parent is not None else Vector3()
        return parent_position + self._position

    @world_position.setter
    def world_position(self, value: Vector3):
        parent_position = self.parent.world_position if self.parent is not None else Vector3()
        self.position = value - parent_position

    @property
    def world_rotation(self) -> Quaternion:
        parent_rotation = self.parent.world_rotation if self.parent is not None else Quaternion()
        return parent_rotation * self._rotation

    @world_rotation.setter
    def world_rotation(self, value: Quaternion):
        parent_rotation = self.parent.world_rotation if self.parent is not None else Quaternion()
        self.rotation = parent_rotation.conjugate * value

    @property
    def world_scale(self) -> Vector3:
        parent_scale = self.parent.world_scale if self.parent is not None else Vector3(1, 1, 1)
        return parent_scale * self._scale

    @world_scale.setter
    def world_scale(self, value: Vector3):
        parent_scale = self.parent.world_scale if self.parent is not None else Vector3(1, 1, 1)
        if parent_scale.x == 0:
            parent_scale.x = 1
        if parent_scale.y == 0:
            parent_scale.y = 1
        if parent_scale.z == 0:
            parent_scale.z = 1
        self.scale = value / parent_scale

    def _calculate_local_matrix(self) -> Matrix44:
        return (
            Matrix44.from_translation(self.position) *
            Matrix44.from_rotation(self.rotation) *
            Matrix44.from_scale(self.scale)
        )

    @property
    def children(self) -> 'Sequence[Node3D]':
        return cast(Sequence[Node3D], super().children)

    def add_child(self, child: 'Node3D', update_parent: bool = True):
        super().add_child(child, update_parent=update_parent)

    def remove_child(self, child: 'Node3D', update_parent: bool = True):
        super().remove_child(child, update_parent=update_parent)

    def has_child(self, child: 'Node3D') -> bool:
        return super().has_child(child)
