from tinycam.project import CncProject
from tinycam.ui.view import CncView
from PySide6 import QtCore, QtGui


class CncTool(QtCore.QObject):
    def __init__(
        self,
        project: CncProject,
        view: CncView,
        action: QtGui.QAction | None = None,
    ):
        super().__init__()
        self.project = project
        self.view = view
        self.action = action

    def activate(self):
        if self.action is not None:
            self.action.setChecked(True)

    def deactivate(self):
        if self.action is not None:
            self.action.setChecked(False)

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        return False
