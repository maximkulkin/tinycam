from tinycam.project import CncProject
from tinycam.ui.view import CncView
from PySide6 import QtCore


class CncTool(QtCore.QObject):
    def __init__(self, project: CncProject, view: CncView):
        super().__init__()
        self.project = project
        self.view = view

    def activate(self):
        self.view.installEventFilter(self)

    def deactivate(self):
        self.view.removeEventFilter(self)

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        return False
