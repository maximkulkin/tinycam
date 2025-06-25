from itertools import chain
from typing import Callable

import numpy as np
from PySide6 import QtGui, QtCore
from tinycam.types import Vector2, Vector4


def qcolor_to_vec4(color: QtGui.QColor) -> Vector4:
    return Vector4(color.redF(), color.greenF(), color.blueF(), color.alphaF())


def vector2(
    point: np.ndarray | tuple[float, float] | QtCore.QPoint | QtCore.QPointF,
) -> Vector2:
    if isinstance(point, QtCore.QPoint):
        return Vector2(point.x(), point.y())
    elif isinstance(point, QtCore.QPointF):
        return Vector2(point.x(), point.y())
    else:
        return Vector2(point[0], point[1])


def point_inside_polygon(p: Vector2, polygon: list[Vector2]) -> bool:
    count = 0
    for (p1, p2) in zip(polygon, chain(polygon[1:], [polygon[0]])):
        if (p.y < p1.y) == (p.y < p2.y):
            continue

        if ((p1.y == p2.y) or p.x < p1.x + (p.y - p1.y) / (p2.y - p1.y) * (p2.x - p1.x)):
            count += 1
    return count % 2 == 1


def clear_layout(layout):
    while layout.count() > 0:
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def schedule(callback: Callable[[], None]):
    QtCore.QTimer.singleShot(0, callback)


def load_icon(path: str, bg_color: QtGui.QColor = QtGui.QColor('white')) -> QtGui.QIcon:
    img = QtGui.QPixmap(path)
    painter = QtGui.QPainter(img)
    painter.setCompositionMode(
        QtGui.QPainter.CompositionMode.CompositionMode_SourceIn
    )
    painter.fillRect(img.rect(), bg_color)
    painter.end()
    return QtGui.QIcon(img)
