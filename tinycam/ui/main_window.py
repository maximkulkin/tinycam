from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt

from tinycam.globals import CncGlobals
from tinycam.formats import excellon, gerber
from tinycam.project import GerberItem, ExcellonItem
from tinycam.ui.visualization import CncVisualization
from tinycam.ui.preview_3d import CncPreview3DView
from tinycam.ui.project import CncProjectWindow
from tinycam.ui.tool_options import CncToolOptionsWindow
from tinycam.ui.settings import CncSettingsDialog


class CncMainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resize(600, 400)

        self.project = CncGlobals.APP.project
        self.project_view = CncVisualization(self.project, self)

        self.preview_view = CncPreview3DView(self)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self.project_view, 'Project')
        self.tabs.addTab(self.preview_view, 'Preview')

        self.setCentralWidget(self.tabs)

        self.menu = QtWidgets.QMenuBar()
        self.file_menu = self.menu.addMenu("File")
        self.file_menu.addAction('Import Drawing', self._import_file,
                                 shortcut='Ctrl+o')

        undo_action = CncGlobals.APP.undo_stack.createUndoAction(self, "&Undo")
        undo_action.setIcon(QtGui.QIcon(":/icons/undo.png"))
        undo_action.setShortcuts(QtGui.QKeySequence.Undo)

        redo_action = CncGlobals.APP.undo_stack.createRedoAction(self, "&Redo")
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
        self.toolbar.setObjectName('Toolbar')
        self.addToolBar(self.toolbar)
        self.toolbar.addAction('Import', self._import_file)
        self.toolbar.addAction('Zoom To Fit', self.project_view.zoom_to_fit)

        self.statusbar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusbar)

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

        self.view_menu.addSeparator()
        self.view_menu.addAction('Zoom In', self.project_view.zoom_in,
                                 shortcut='Ctrl++')
        self.view_menu.addAction('Zoom Out', self.project_view.zoom_out,
                                 shortcut='Ctrl+-')
        self.view_menu.addAction('Zoom To Fit', self.project_view.zoom_to_fit,
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

        def critical_error(text):
            QtWidgets.QMessageBox.critical(self, 'Import Drawing', text)

        item = None
        if filename.endswith('.gbr'):
            try:
                item = GerberItem.from_file(filename)
            except gerber.GerberError as e:
                critical_error(f'Error parsing Gerber file: {e}')
                return

        elif filename.endswith('.drl'):
            try:
                item = ExcellonItem.from_file(filename)
            except excellon.ExcellonError as e:
                QtWidgets.QMessageBox.critical(
                    self, 'Import Drawing',
                    f'Error parsing Excellon file: {e}',
                )
                return
        else:
            if item is None:
                try:
                    item = GerberItem.from_file(filename)
                except gerber.GerberError:
                    pass

            if item is None:
                try:
                    item = ExcellonItem.from_file(filename)
                except excellon.ExcellonError:
                    pass

        if item is None:
            QtWidgets.QMessageBox.critical(
                self, 'Import Drawing',
                f'File format is not recognized for {filename}',
            )
            return

        CncGlobals.APP.project.items.append(item)

    def _edit_settings(self):
        settings_dialog = CncSettingsDialog(CncGlobals.APP.settings, self)
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

        self.project_view.zoom_to_fit()

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


