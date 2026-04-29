from PySide6 import QtCore, QtWidgets, QtGui
from typing import cast

from tinycam.formats import excellon, gerber
from tinycam.globals import GLOBALS
from tinycam.project import CncProject, GerberItem, ExcellonItem, SvgItem
from tinycam.reactive import ReactiveVar
from tinycam.settings import CncSettings, BufferReader, BufferWriter, get_serializer
from tinycam.tasks import TaskManager
from tinycam.math_types import Vector2


class CncApplicationState:
    snap_to_grid = ReactiveVar[bool](False)
    snap_step = ReactiveVar[Vector2](Vector2(1, 1))


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
        self.state = CncApplicationState()

        self._load_settings()
        self.aboutToQuit.connect(self._save_settings)

        self.state.snap_to_grid.value = self.settings.get('general/snapping/enabled')
        self.state.snap_step.value = self.settings.get('general/snapping/default_step')

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

    def event(self, event: QtCore.QEvent) -> bool:
        if isinstance(event, QtGui.QFileOpenEvent):
            self.import_file(event.file())
            return True
        return super().event(event)

    def import_file(self, filename: str) -> bool:
        from tinycam.ui.commands import ImportFileCommand

        item = None
        if filename.endswith('.svg'):
            item = self._try_import_svg(filename)
        elif filename.endswith('.gbr'):
            item = self._try_import_gerber(filename)
        elif filename.endswith('.drl'):
            item = self._try_import_excellon(filename)
        else:
            item = (
                self._try_import_svg(filename, silent=True) or
                self._try_import_gerber(filename, silent=True) or
                self._try_import_excellon(filename, silent=True)
            )

        if item is None:
            return False

        self.undo_stack.push(ImportFileCommand(filename, item))
        return True

    def _try_import_svg(self, filename: str, silent: bool = False) -> SvgItem | None:
        try:
            return SvgItem.from_file(filename)
        except Exception as e:
            if not silent:
                QtWidgets.QMessageBox.critical(None, 'Import SVG', f'Error parsing SVG file: {e}')
            return None

    def _try_import_gerber(self, filename: str, silent: bool = False) -> GerberItem | None:
        try:
            return GerberItem.from_file(filename)
        except gerber.GerberError as e:
            if not silent:
                QtWidgets.QMessageBox.critical(None, 'Import Gerber', f'Error parsing Gerber file: {e}')
            return None

    def _try_import_excellon(self, filename: str, silent: bool = False) -> ExcellonItem | None:
        try:
            return ExcellonItem.from_file(filename)
        except excellon.ExcellonError as e:
            if not silent:
                QtWidgets.QMessageBox.critical(None, 'Import Excellon', f'Error parsing Excellon file: {e}')
            return None

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
