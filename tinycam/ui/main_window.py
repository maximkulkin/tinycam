from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt

from tinycam.globals import GLOBALS
from tinycam.formats import excellon, gerber
from tinycam.project import GerberItem, ExcellonItem
from tinycam.ui.commands import ImportFileCommand
from tinycam.ui.canvas_2d import CncCanvas2D
from tinycam.ui.preview_3d import CncPreview3D
from tinycam.ui.project import CncProjectWindow
from tinycam.ui.tool_options import CncToolOptionsWindow
from tinycam.ui.cnc_controller import CncControllerWindow
from tinycam.ui.settings import CncSettingsDialog


class CncMainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resize(600, 400)

        self.project = GLOBALS.APP.project

        self.canvas_2d = CncCanvas2D(project=self.project, parent=self)
        self.preview_3d = CncPreview3D(project=self.project, parent=self)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self.canvas_2d, '2D')
        self.tabs.addTab(self.preview_3d, '3D')
        self.tabs.setCurrentIndex(0)

        self.setCentralWidget(self.tabs)

        self.menu = QtWidgets.QMenuBar()
        self.file_menu = self.menu.addMenu("File")
        self.file_menu.addAction('Import Drawing', self._import_file,
                                 shortcut='Ctrl+o')

        undo_action = GLOBALS.APP.undo_stack.createUndoAction(self, "&Undo")
        undo_action.setIcon(QtGui.QIcon(":/icons/undo.png"))
        undo_action.setShortcuts(QtGui.QKeySequence.Undo)

        redo_action = GLOBALS.APP.undo_stack.createRedoAction(self, "&Redo")
        redo_action.setIcon(QtGui.QIcon(":/icons/redo.png"))
        redo_action.setShortcuts(QtGui.QKeySequence.Redo)

        self.edit_menu = self.menu.addMenu("Edit")
        self.edit_menu.addAction(undo_action)
        self.edit_menu.addAction(redo_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction('Edit Settings', self._edit_settings,
                                 shortcut='Ctrl+,')

        self.view_menu = self.menu.addMenu("View")

        self.setMenuBar(self.menu)

        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.setObjectName('main_toolbar')
        self.toolbar.setWindowTitle('Toolbar')
        self.addToolBar(self.toolbar)
        self.toolbar.addAction('Import', self._import_file)
        self.toolbar.addAction('Zoom In', 'Ctrl++', self._zoom_in)
        self.toolbar.addAction('Zoom Out', 'Ctrl+-', self._zoom_out)
        self.toolbar.addAction('Zoom To Fit', 'Ctrl+=', self._zoom_to_fit)

        self.statusbar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusbar)
        GLOBALS.APP.task_manager.statusbar = self.statusbar

        self._windows = []
        self._windows_menu = {}

        self._add_dock_window(
            CncProjectWindow(self.project), Qt.LeftDockWidgetArea,
            shortcut='Ctrl+1',
        )
        self._add_dock_window(
            CncToolOptionsWindow(self.project), Qt.RightDockWidgetArea,
            shortcut='Ctrl+2',
        )
        self._add_dock_window(
            CncControllerWindow(self.project), Qt.RightDockWidgetArea,
            shortcut='Ctrl+3',
        )

        self.view_menu.addSeparator()
        self.view_menu.addAction('Zoom In', self._zoom_in, shortcut='Ctrl++')
        self.view_menu.addAction('Zoom Out', self._zoom_out, shortcut='Ctrl+-')
        self.view_menu.addAction('Zoom To Fit', self._zoom_to_fit,
                                 shortcut='Ctrl+=')
        self.view_menu.addSeparator()

        self._load_settings()

    def _import_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption='Import Drawing',
            filter='Gerber (*.gbr);;Excellon (*.drl);;All files (*)'
        )
        if filename == '':
            return

        item = None
        if filename.endswith('.gbr'):
            item = self._import_gerber(filename)
        elif filename.endswith('.drl'):
            item = self._import_excellon(filename)
        else:
            if item is None:
                item = self._import_gerber(filename, silent=True)

            if item is None:
                item = self._import_excellon(filename, silent=True)

        if item is None:
            QtWidgets.QMessageBox.critical(
                self, 'Import Drawing',
                f'File format is not recognized for {filename}',
            )
            return

        GLOBALS.APP.undo_stack.push(ImportFileCommand(filename, item))

    def _import_gerber(self, filename: str, silent: bool = False) -> GerberItem | None:
        try:
            return GerberItem.from_file(filename)
        except gerber.GerberError as e:
            if not silent:
                QtWidgets.QMessageBox.critical(
                    self, 'Import Drawing', f'Error parsing Gerber file: {e}',
                )
            return None

    def _import_excellon(self, filename: str, silent: bool = False) -> ExcellonItem | None:
        try:
            return ExcellonItem.from_file(filename)
        except excellon.ExcellonError as e:
            if not silent:
                QtWidgets.QMessageBox.critical(
                    self, 'Import Drawing',
                    f'Error parsing Excellon file: {e}',
                )
            return None

    def _zoom_in(self):
        match self.tabs.currentIndex():
            case 0:
                self.canvas_2d.zoom_in()
            case 1:
                self.preview_3d.zoom_in()

    def _zoom_out(self):
        match self.tabs.currentIndex():
            case 0:
                self.canvas_2d.zoom_out()
            case 1:
                self.preview_3d.zoom_out()

    def _zoom_to_fit(self):
        match self.tabs.currentIndex():
            case 0:
                self.canvas_2d.zoom_to_fit()
            case 1:
                self.preview_3d.zoom_to_fit()

    def _edit_settings(self):
        settings_dialog = CncSettingsDialog(GLOBALS.APP.settings, self)
        settings_dialog.exec()

    def _add_dock_window(self, window, area, shortcut=''):
        self._windows.append(window)
        self.addDockWidget(area, window)
        action = self.view_menu.addAction(
            window.windowTitle(), lambda: self._toggle_window(window),
            shortcut=shortcut)
        action.setCheckable(True)
        self._windows_menu[window] = action

    def _toggle_window(self, window):
        if window.isVisible():
            window.hide()
        else:
            window.show()

        if window in self._windows_menu:
            self._windows_menu.get(window).setChecked(window.isVisible())

    def showEvent(self, event):
        super().showEvent(event)

        for window in self._windows:
            self._windows_menu[window].setChecked(window.isVisible())

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    def _save_settings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("main_window")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.endGroup()

    def _load_settings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("main_window")
        self.restoreGeometry(settings.value("geometry"))
        self.restoreState(settings.value("windowState"))
        settings.endGroup()
