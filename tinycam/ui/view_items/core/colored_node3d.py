from typing import Protocol, runtime_checkable

from tinycam.math_types import Vector4
from tinycam.ui.view import Context
from tinycam.ui.view_items.core.node3d import Node3D


@runtime_checkable
class Colored(Protocol):
    @property
    def color(self) -> Vector4: ...

    @color.setter
    def color(self, value: Vector4): ...


class ColoredNode3D(Node3D):
    def __init__(self, context: Context, color: Vector4 = Vector4(1, 1, 1, 1)):
        super().__init__(context)
        self._color = color

    @property
    def color(self) -> Vector4:
        return self._color

    @color.setter
    def color(self, value: Vector4):
        self._color = value
        for child in self.children:
            if isinstance(child, Colored):
                child.color = value
