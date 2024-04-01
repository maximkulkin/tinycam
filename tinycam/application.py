from PySide6 import QtCore, QtWidgets, QtGui

from tinycam.globals import GLOBALS
from tinycam.project import CncProject


class CncApplication(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = CncProject()
        self.settings = GLOBALS.SETTINGS
        self.undo_stack = QtGui.QUndoStack()

        self._load_settings()

    def _save_settings(self):
        settings = QtCore.Settings()
        settings.beginGroup("settings")

        for setting in self.settings:
            if self.settings.is_default(setting.path):
                continue

            value = self.settings.get(setting.path)
            settings.setValue(setting.path, setting.type.serialize(value))

        settings.endGroup()

    def _load_settings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("settings")

        for setting in self.settings:
            value = settings.value(setting.path, None)
            if value is None:
                value = setting.default
            else:
                try:
                    value = setting.type.deserialize(value)
                except CncSettingError as e:
                    print(e.message)
                    continue

                self.settings.set(setting.path, value)

        settings.endGroup()


