from tinycam.project import CncProject
from tinycam.signals import Signal
from tinycam.types import Vector2, Vector3
from tinycam.ui.view import CncView
from tinycam.ui.utils import vector2
from PySide6 import QtCore


class CncTool(QtCore.QObject):
    activated = Signal()
    deactivated = Signal()

    def __init__(
        self,
        project: CncProject,
        view: CncView,
    ):
        super().__init__()
        self.project = project
        self.view = view

    def activate(self):
        self.activated.emit()

    def deactivate(self):
        self.deactivated.emit()

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        return False

    def _screen_to_world_point(
        self,
        point: Vector2 | QtCore.QPoint | QtCore.QPointF,
    ) -> Vector3:
        return self.view.camera.screen_to_world_point(vector2(point))
