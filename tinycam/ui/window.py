from PySide6 import QtCore, QtWidgets


class CncWindow(QtWidgets.QDockWidget):
    visibilityChanged = QtCore.Signal()

    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = project
        self.setMinimumSize(200, 200)

    def showEvent(self, event):
        self.visibilityChanged.emit()
        super().showEvent(event)

    def hideEvent(self, event):
        self.visibilityChanged.emit()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.hide()
        event.accept()
