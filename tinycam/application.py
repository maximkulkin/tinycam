from PySide6 import QtCore, QtWidgets, QtGui
from typing import cast

from tinycam.globals import GLOBALS
from tinycam.project import CncProject
from tinycam.settings import CncSettings
from tinycam.tasks import TaskManager


class CncApplication(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project: CncProject = CncProject()
        self.settings: CncSettings = GLOBALS.SETTINGS
        self.undo_stack: QtGui.QUndoStack = QtGui.QUndoStack()
        self.task_manager: TaskManager = TaskManager()

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
                    setting.load(cast(str, data))
                except Exception as e:
                    print(f'Failed to laod setting {setting.path}: {e}')
                    continue

        settings.endGroup()
