from PySide6 import QtCore
from PySide6.QtCore import Qt
from tinycam.types import Vector2, Vector4
from tinycam.ui.tools import CncTool
from tinycam.ui.view_items.canvas import Circle, Rectangle


def vector2(point: QtCore.QPoint | QtCore.QPointF) -> Vector2:
    return Vector2(point.x(), point.y())


class MarkerTool(CncTool):
    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if (event.type() == QtCore.QEvent.MouseButtonPress and
                event.button() & Qt.LeftButton):
            self.view.add_item(Circle(
                self.view.ctx,
                center=vector2(event.position()),
                radius=20,
                fill_color=Vector4(1, 1, 0, 0.3),
                edge_color=Vector4(1, 1, 0, 0.6),
                edge_width=2,
            ))
            # self.view.add_item(Rectangle(
            #     self.view.ctx,
            #     center=vector2(event.position()),
            #     size=Vector2(10, 10),
            #     fill_color=Vector4(1, 1, 0, 1),
            # ))
            return True

        return False
