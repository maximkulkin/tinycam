from PySide6 import QtCore, QtWidgets, QtGui
from typing import cast

from tinycam.globals import GLOBALS
from tinycam.project import CncProject
from tinycam.settings import CncSettings, BufferReader, BufferWriter, get_serializer
from tinycam.tasks import TaskManager


class CncApplication(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setOrganizationDomain('tinycam.com')
        self.setApplicationName('tinycam')
        self.setApplicationDisplayName('TinyCAM')

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
            serializer = get_serializer(setting.type)
            if serializer is None:
                print(f"Can't find serializer for setting {setting.path}")
                continue

            writer = BufferWriter()
            serializer.serialize(setting.value, writer)
            settings.setValue(setting.path, writer.data)

        settings.endGroup()

    def _load_settings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("settings")

        for setting in self.settings:
            serializer = get_serializer(setting.type)
            if serializer is None:
                print(f"Can't find deserializer for setting {setting.path}")
                continue

            data = settings.value(setting.path, None)
            if data is not None:
                try:
                    reader = BufferReader(cast(bytes, data))
                    setting.value = serializer.deserialize(reader)
                except Exception as e:
                    print(f'Failed to load setting {setting.path}: {e}')
                    continue

        settings.endGroup()
