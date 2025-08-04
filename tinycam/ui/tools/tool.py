from tinycam.project import CncProject
from tinycam.signals import Signal
from tinycam.ui.view import CncView
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
