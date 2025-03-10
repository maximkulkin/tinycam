from typing import cast

from PySide6 import QtCore
from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtGui import QMouseEvent

from tinycam.types import Vector2, Vector4
from tinycam.ui.tools import CncTool
from tinycam.ui.view_items.canvas import Circle


def vector2(point: QtCore.QPoint | QtCore.QPointF) -> Vector2:
    return Vector2(point.x(), point.y())


class MarkerTool(CncTool):
    def eventFilter(self, widget: QObject, event: QEvent) -> bool:
        assert(self.view.ctx is not None)

        mouse_event = cast(QMouseEvent, event)
        if (event.type() == QEvent.Type.MouseButtonPress and
                mouse_event.button() & Qt.MouseButton.LeftButton):
            self.view.add_item(Circle(
                self.view.ctx,
                center=vector2(mouse_event.position()),
                radius=20,
                fill_color=Vector4(1, 1, 0, 0.3),
                edge_color=Vector4(1, 1, 0, 0.6),
                edge_width=2,
            ))
            return True

        return False
