from tinycam.project import CncProject
from tinycam.ui.view import CncView
from PySide6 import QtCore


class CncTool(QtCore.QObject):
    def __init__(self, project: CncProject, view: CncView):
        self.project = project
        self.view = view

    def activate(self):
        pass

    def deactivate(self):
        pass

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        return False
