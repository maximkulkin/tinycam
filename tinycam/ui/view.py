from PySide6 import QtCore
from functools import reduce
from tinycam.ui.camera import Camera
from tinycam.types import Vector3
from typing import Optional


def combine_bounds(b1, b2):
    return (min(b1[0], b2[0]), min(b1[1], b2[1]), max(b1[2], b2[2]), max(b1[3], b2[3]))


class CncView:
    ZOOM_FACTOR = 0.8

    view_updated = QtCore.Signal()

    @property
    def camera(self) -> Camera:
        raise NotImplementedError()

    def screen_to_canvas_point(self, p: QtCore.QPoint, depth: float = 0.0) -> Vector3:
        raise NotImplementedError()

    def canvas_to_screen_point(self, p: Vector3) -> QtCore.QPoint:
        raise NotImplementedError()

    @property
    def size(self) -> QtCore.QSize:
        return QtCore.QSize((self.width(), self.height()))

    @property
    def center(self) -> QtCore.QPoint:
        return QtCore.QPoint(self.width() * 0.5, self.height() * 0.5)

    # def _zoom(self, amount: float, point: Optional[QtCore.QPointF] = None):
    #     raise NotImplementedError()

    # def _zoom_region(self, region: QtCore.QRectF):
    #     raise NotImplementedError()

    # def zoom_in(self):
    #     self._zoom(1.0 / self.ZOOM_FACTOR, self.center)

    # def zoom_out(self):
    #     self._zoom(self.ZOOM_FACTOR, self.center)

    # def zoom_to_fit(self):
    #     if not self.project.items:
    #         return

    #     bounds = reduce(combine_bounds, [
    #         item.geometry.bounds for item in self.project.items
    #     ])

    #     self._zoom_region(QtCore.QRectF(
    #         bounds[0],
    #         bounds[1],
    #         bounds[2] - bounds[0],
    #         bounds[3] - bounds[1],
    #     ))
