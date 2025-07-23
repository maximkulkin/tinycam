from typing import Callable

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt

from tinycam.globals import GLOBALS
from tinycam.formats import excellon, gerber
from tinycam.project import GerberItem, ExcellonItem
from tinycam.settings import SETTINGS, ControlType
from tinycam.types import Vector2
from tinycam.ui.commands import ImportFileCommand, FlipHorizontallyCommand, FlipVerticallyCommand
from tinycam.ui.canvas_2d import CncCanvas2D
from tinycam.ui.preview_3d import CncPreview3D
from tinycam.ui.project import CncProjectWindow
from tinycam.ui.tools import CncTool, SelectTool, TransformTool
from tinycam.ui.item_properties import CncProjectItemPropertiesWindow
from tinycam.ui.cnc_controller import (
    CncControllerStateDisplayWindow, CncControllerJogControlsWindow,
    CncControllerControlsWindow, CncControllerConsoleWindow,
    CncConnectionToolbar,
)
from tinycam.ui.settings import CncSettingsDialog
from tinycam.ui.utils import load_icon


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
        self.view_menu.addAction(
            '2D', lambda: self.tabs.setCurrentIndex(0),
            shortcut='Ctrl+1',
        )
        self.view_menu.addAction(
            '3D', lambda: self.tabs.setCurrentIndex(1),
            shortcut='Ctrl+2',
        )

        self.setMenuBar(self.menu)

        import_file_action = self._make_action(
            'Import File', self._import_file,
            icon=':/icons/file_import.svg',
            shortcut='Ctrl+o',
        )

        zoom_in_action = self._make_action(
            'Zoom In', self._zoom_in,
            icon=':/icons/zoom_in.svg',
            shortcut='Ctrl++',
        )
        zoom_out_action = self._make_action(
            'Zoom Out', self._zoom_out,
            icon=':/icons/zoom_out.svg',
            shortcut='Ctrl+-',
        )
        zoom_fit_action = self._make_action(
            'Zoom To Fit', self._zoom_to_fit,
            icon=':/icons/zoom_fit.svg',
            shortcut='Ctrl+=',
        )

        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.setObjectName('main_toolbar')
        self.toolbar.setWindowTitle('Toolbar')
        self.addToolBar(self.toolbar)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.toolbar.addAction(import_file_action)

        self.zoom_toolbar = QtWidgets.QToolBar()
        self.zoom_toolbar.setObjectName('zoom_toolbar')
        self.zoom_toolbar.setWindowTitle('Zoom Toolbar')
        self.zoom_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addToolBar(self.zoom_toolbar)
        self.zoom_toolbar.addAction(zoom_in_action)
        self.zoom_toolbar.addAction(zoom_out_action)
        self.zoom_toolbar.addAction(zoom_fit_action)

        self._select_tool = SelectTool(self.project, self.canvas_2d)
        select_tool_action = self._make_action(
            'Select Tool', lambda: self._activate_tool(self._select_tool),
            icon=':/icons/select_tool.svg',
            shortcut='v',
        )
        select_tool_action.setCheckable(True)
        self._select_tool.action = select_tool_action

        self._transform_tool = TransformTool(self.project, self.canvas_2d)
        transform_tool_action = self._make_action(
            'Transform Tool', lambda: self._activate_tool(self._transform_tool),
            icon=':/icons/transform_tool.svg',
            shortcut='e',
        )
        transform_tool_action.setCheckable(True)
        self._transform_tool.action = transform_tool_action

        self._flip_horizontally_action = self._make_action(
            'Flip Horizontally', self._flip_horizontally,
            icon=':/icons/flip_horizontally.svg',
        )
        self._flip_vertically_action = self._make_action(
            'Flip Vertically', self._flip_vertically,
            icon=':/icons/flip_vertically.svg',
        )

        self.tools_toolbar = QtWidgets.QToolBar()
        self.tools_toolbar.setObjectName('tools_toolbar')
        self.tools_toolbar.setWindowTitle('Tools Toolbar')
        self.addToolBar(self.tools_toolbar)
        self.tools_toolbar.addAction(select_tool_action)
        self.tools_toolbar.addAction(transform_tool_action)
        self.tools_toolbar.addAction(self._flip_horizontally_action)
        self.tools_toolbar.addAction(self._flip_vertically_action)

        self._activate_tool(self._select_tool)

        self.cnc_connection_toolbar = CncConnectionToolbar()
        self.addToolBar(self.cnc_connection_toolbar)

        self.statusbar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusbar)

        self._coordinate_info = CoordinateInfo()
        self._control_type_info = ControlTypeInfo()
        self.statusbar.addPermanentWidget(self._coordinate_info)
        self.statusbar.addPermanentWidget(self._control_type_info)
        self.canvas_2d.coordinateChanged.connect(self._coordinate_info.setCoordinates)
        self.preview_3d.coordinateChanged.connect(self._coordinate_info.setCoordinates)

        GLOBALS.APP.task_manager.statusbar = self.statusbar

        self._windows = []
        self._windows_menu = {}

        self._add_dock_window(
            CncProjectWindow(self.project),
            Qt.DockWidgetArea.LeftDockWidgetArea,
            shortcut='Ctrl+3',
        )
        self._add_dock_window(
            CncProjectItemPropertiesWindow(self.project),
            Qt.DockWidgetArea.RightDockWidgetArea,
            shortcut='Ctrl+4',
        )
        self._add_dock_window(
            CncControllerStateDisplayWindow(self.project, GLOBALS.CNC_CONTROLLER),
            Qt.DockWidgetArea.RightDockWidgetArea,
        )
        self._add_dock_window(
            CncControllerJogControlsWindow(self.project, GLOBALS.CNC_CONTROLLER),
            Qt.DockWidgetArea.RightDockWidgetArea,
        )
        self._add_dock_window(
            CncControllerControlsWindow(self.project, GLOBALS.CNC_CONTROLLER),
            Qt.DockWidgetArea.RightDockWidgetArea,
        )
        self._add_dock_window(
            CncControllerConsoleWindow(self.project),
            Qt.DockWidgetArea.BottomDockWidgetArea,
        )

        self.file_menu.addAction(import_file_action)

        self.view_menu.addSeparator()
        self.view_menu.addAction(zoom_in_action)
        self.view_menu.addAction(zoom_out_action)
        self.view_menu.addAction(zoom_fit_action)
        self.view_menu.addSeparator()

        self._load_settings()

    def _make_action(
        self,
        label: str,
        callback: Callable[[], None],
        icon: str | None = None,
        shortcut: str | None = None
    ) -> QtGui.QAction:
        action = QtGui.QAction(label, self)
        action.triggered.connect(callback)
        if icon is not None:
            action.setIcon(QtGui.QIcon(icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        return action

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

    def _activate_tool(self, tool: CncTool):
        self.canvas_2d.tool = tool

    def _flip_horizontally(self):
        GLOBALS.APP.undo_stack.push(FlipHorizontallyCommand(
            list(self.project.selection),
        ))

    def _flip_vertically(self):
        GLOBALS.APP.undo_stack.push(FlipVerticallyCommand(
            list(self.project.selection),
        ))

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


class CoordinateInfo(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setFrameStyle(QtWidgets.QFrame.Panel)

        self._x_label = QtWidgets.QLabel('0.00')
        self._x_label.setFixedWidth(50)
        self._x_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._y_label = QtWidgets.QLabel('0.00')
        self._y_label.setFixedWidth(50)
        self._y_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        layout.addWidget(QtWidgets.QLabel('X: '))
        layout.addWidget(self._x_label)
        layout.addWidget(QtWidgets.QLabel('Y: '))
        layout.addWidget(self._y_label)

        self.setLayout(layout)

    @QtCore.Slot()
    def setCoordinates(self, coords: Vector2):
        self._x_label.setText(f'{coords.x:.2f}')
        self._y_label.setText(f'{coords.y:.2f}')


class ControlTypeInfo(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        self.setFrameStyle(QtWidgets.QFrame.Panel)

        self._mouse_icon = load_icon('icons/mouse.svg')
        self._touchpad_icon = load_icon('icons/touchpad.svg')

        self._button = QtWidgets.QToolButton()
        self._button.clicked.connect(self._on_button_clicked)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._button)

        self.setLayout(layout)

        setting = SETTINGS['general/control_type']
        setting.changed.connect(self._on_control_type_changed)
        self._on_control_type_changed(setting.value)

    def _on_control_type_changed(self, value: ControlType):
        match value:
            case ControlType.MOUSE:
                self._button.setIcon(self._mouse_icon)
                self._button.setToolTip('Control with mouse')
            case ControlType.TOUCHPAD:
                self._button.setIcon(self._touchpad_icon)
                self._button.setToolTip('Control with touchpad')

    def _on_button_clicked(self):
        setting = SETTINGS['general/control_type']
        match setting.value:
            case ControlType.MOUSE:
                setting.value = ControlType.TOUCHPAD
            case ControlType.TOUCHPAD:
                setting.value = ControlType.MOUSE
