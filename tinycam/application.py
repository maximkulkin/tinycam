from PySide6 import QtCore, QtWidgets, QtGui

from tinycam.globals import GLOBALS
from tinycam.project import CncProject
from tinycam.tasks import TaskManager


class CncApplication(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = CncProject()
        self.settings = GLOBALS.SETTINGS
        self.undo_stack = QtGui.QUndoStack()
        self.task_manager = TaskManager()

        self._load_settings()
        self.aboutToQuit.connect(self._save_settings)

    def _save_settings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("settings")

        for setting in self.settings:
            settings.setValue(setting.path, setting.save())

        settings.endGroup()

    def _load_settings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("settings")

        for setting in self.settings:
            data = settings.value(setting.path, None)
            if data is not None:
                try:
                    setting.load(data)
                except Exception:
                    continue

        settings.endGroup()
