import numpy as np

from tinycam.types import Vector2, Vector4
from tinycam.ui.view import Context
from tinycam.ui.view_items.core.line2d import Line2D
from tinycam.ui.view_items.core.node3d import Node3D

type any_float = float | np.float32


class Grid(Node3D):

    def __init__(self, context: Context, size: Vector2):
        super().__init__(context)

        self._line((0, size.y), size)
        self._line((size.x, 0), size)

        grid_spacing = Vector2(10, 10)
        x = grid_spacing.x
        while x < size.x:
            self._line((x, 0), (x, size.y)) 
            x += grid_spacing.x

        y = grid_spacing.y
        while y < size.y:
            self._line((0, y), (size.x, y))
            y += grid_spacing.y

        self._line((0, 0), (size.x, 0), color=Vector4(1, 0, 0, 1))
        self._line((0, 0), (0, size.y), color=Vector4(0, 1, 0, 1))

    def _line(
        self,
        p1: Vector2 | tuple[any_float, any_float],
        p2: Vector2 | tuple[any_float, any_float],
        color: Vector4 = Vector4(0.2, 0.2, 0.2, 1.0),
    ):
        self.add_child(Line2D(self.context, [Vector2(p1), Vector2(p2)], color=color))

