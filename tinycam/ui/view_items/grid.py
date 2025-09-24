from PySide6 import QtGui
from PySide6.QtCore import Qt
import numpy as np

from tinycam.types import Box, Vector2, Vector3, Vector4
from tinycam.ui.view import Context
from tinycam.ui.view_items.core.line2d import Line2D
from tinycam.ui.view_items.core.node3d import Node3D
from tinycam.ui.view_items.core.text import FontAtlas, Text

type any_float = float | np.float32


class Grid(Node3D):

    def __init__(self, context: Context, size: Vector2):
        super().__init__(context)

        self._size = size

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

        self._line((0, 0), (size.x + grid_spacing.x * 0.5, 0), color=Vector4(1, 0, 0, 1))
        self._line((0, 0), (0, size.y + grid_spacing.y * 0.5), color=Vector4(0, 1, 0, 1))

        font = QtGui.QFont('Arial')
        font.setPointSize(48)
        self._font_atlas = FontAtlas.create(self.context, font, '0123456789.XY')

        x = grid_spacing.x
        while x <= size.x:
            self._text(
                (x, 0),
                str(x),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            ) 

            x += grid_spacing.x

        y = grid_spacing.y
        while y <= size.y:
            self._text(
                (0, y),
                str(y),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )

            y += grid_spacing.y

        self._text(
            (0, 0),
            '0',
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        )

        self._text(
            (size.x + grid_spacing.x * 0.5, 0),
            'X',
            color=Vector4(1, 0, 0, 1),
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )

        self._text(
            (0, size.y + grid_spacing.y * 0.5),
            'Y',
            color=Vector4(0, 1, 0, 1),
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
        )

    @property
    def bounds(self) -> Box:
        return Box(
            x=self.world_position.x - 20,
            y=self.world_position.y - 20,
            z=self.world_position.z - 0.5,
            width=self._size.x + 40,
            height=self._size.y + 40,
            depth=1.0,
        )

    def _line(
        self,
        p1: Vector2 | tuple[any_float, any_float],
        p2: Vector2 | tuple[any_float, any_float],
        color: Vector4 = Vector4(0.2, 0.2, 0.2, 1.0),
    ):
        self.add_child(Line2D(self.context, [Vector2(p1), Vector2(p2)], color=color))

    def _text(
        self,
        p: Vector2 | tuple[any_float, any_float],
        text: str,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        color: Vector4 = Vector4(0.4, 0.4, 0.4, 1.0),
        margin: int | float | Vector2 = 20,
    ):
        text_node = Text(
            self.context,
            self._font_atlas,
            text,
            color=color,
            alignment=alignment,
            margin=margin,
        )
        text_node.position = Vector3.from_vector2(Vector2(p))
        text_node.scale = Vector3(0.06, 0.06, 1.0)
        self.add_child(text_node)
