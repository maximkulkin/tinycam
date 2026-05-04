import os

from PySide6 import QtCore, QtWidgets, QtGui
from typing import cast

from tinycam.formats import excellon, gerber
from tinycam.globals import GLOBALS
from tinycam.project import CncProject, GerberItem, ExcellonItem, ImageItem, SvgItem
from tinycam.reactive import ReactiveVar
from tinycam.settings import CncSettings, BufferReader, BufferWriter, get_serializer
from tinycam.tasks import TaskManager
from tinycam.math_types import Vector2


class CncApplicationState:
    snap_to_grid = ReactiveVar[bool](False)
    snap_step = ReactiveVar[Vector2](Vector2(1, 1))


class CncApplication(QtWidgets.QApplication):
    project_path_changed = QtCore.Signal()
    file_imported = QtCore.Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setOrganizationDomain('tinycam.com')
        self.setApplicationName('tinycam')
        self.setApplicationDisplayName('TinyCAM')

        self.project: CncProject = CncProject()
        self.settings: CncSettings = GLOBALS.SETTINGS
        self.undo_stack: QtGui.QUndoStack = QtGui.QUndoStack()
        self.task_manager: TaskManager = TaskManager()
        self._project_path: str | None = None
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
        elif any(filename.lower().endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')):
            item = self._try_import_image(filename)
        else:
            item = (
                self._try_import_svg(filename, silent=True) or
                self._try_import_gerber(filename, silent=True) or
                self._try_import_excellon(filename, silent=True)
            )

        if item is None:
            QtWidgets.QMessageBox.critical(None, 'Import Drawing', f'File format is not recognized for {filename}')
            return False

        self.undo_stack.push(ImportFileCommand(filename, item))
        self.file_imported.emit(item)
        return True

    def _try_import_image(self, filename: str, silent: bool = False) -> ImageItem | None:
        try:
            return ImageItem.from_file(filename)
        except Exception as e:
            if not silent:
                QtWidgets.QMessageBox.critical(None, 'Import Image', f'Error loading image file: {e}')
            return None

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

    def _confirm_discard_changes(self) -> bool:
        if self.undo_stack.isClean():
            return True
        filename = os.path.basename(self._project_path) if self._project_path else 'Untitled'
        result = QtWidgets.QMessageBox.question(
            None,
            'Unsaved Changes',
            f'Save changes to "{filename}"?',
            QtWidgets.QMessageBox.StandardButton.Save |
            QtWidgets.QMessageBox.StandardButton.Discard |
            QtWidgets.QMessageBox.StandardButton.Cancel,
            QtWidgets.QMessageBox.StandardButton.Save,
        )
        if result == QtWidgets.QMessageBox.StandardButton.Cancel:
            return False
        if result == QtWidgets.QMessageBox.StandardButton.Save:
            return self.save_project()
        return True

    def new_project(self) -> bool:
        if not self._confirm_discard_changes():
            return False
        self.project.items.clear()
        self.undo_stack.clear()
        self._project_path = None
        self.project_path_changed.emit()
        return True

    def open_project(self, path: str | None = None) -> bool:
        if not self._confirm_discard_changes():
            return False
        if path is None:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                None, 'Open Project', '', 'TinyCAM Projects (*.tinycam)'
            )
            if not path:
                return False
        from tinycam.project.serialization import load_project
        try:
            items = load_project(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, 'Open Project', f'Failed to open project:\n{e}')
            return False
        self.project.items.clear()
        for item in items:
            self.project.items.append(item)
        self.undo_stack.clear()
        self._project_path = path
        self.project_path_changed.emit()
        return True

    def save_project(self) -> bool:
        if self._project_path is None:
            return self.save_project_as()
        return self._save_to_path(self._project_path)

    def save_project_as(self) -> bool:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            None, 'Save Project', '', 'TinyCAM Projects (*.tinycam)'
        )
        if not path:
            return False
        if not path.endswith('.tinycam'):
            path += '.tinycam'
        return self._save_to_path(path)

    def _save_to_path(self, path: str) -> bool:
        from tinycam.project.serialization import save_project
        try:
            save_project(list(self.project.items), path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, 'Save Project', f'Failed to save project:\n{e}')
            return False
        self.undo_stack.setClean()
        self._project_path = path
        self.project_path_changed.emit()
        return True

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
