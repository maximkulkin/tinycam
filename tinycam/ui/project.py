from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt

from tinycam.globals import GLOBALS
from tinycam.project import ExcellonItem, GerberItem
from tinycam.ui.window import CncWindow
from tinycam.ui.commands import (
    CreateIsolateJobCommand,
    CreateDrillJobCommand,
    SetItemsColorCommand,
    DeleteItemsCommand,
)


ITEM_COLORS = [
    QtGui.QColor.fromRgbF(0.6, 0.0, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.6, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.0, 0.6, 0.6),
    QtGui.QColor.fromRgbF(0.6, 0.0, 0.6, 0.6),
    QtGui.QColor.fromRgbF(0.6, 0.6, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.6, 0.6, 0.6),
]


class CncProjectWindow(CncWindow):
    class ItemWidget(QtWidgets.QListWidgetItem):
        def __init__(self, project, item):
            super().__init__(item.name, type=QtWidgets.QListWidgetItem.UserType + 1)
            self.project = project
            self.item = item
            self.setFlags(
                  Qt.ItemIsEnabled
                | Qt.ItemIsEditable
                | Qt.ItemIsSelectable
                | Qt.ItemIsUserCheckable
            )
            self.setCheckState(Qt.Checked if self.item.visible else Qt.Unchecked)

    class ColorBox(QtWidgets.QWidget):
        def __init__(self, color, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.color = color
            self.set = QtCore.QPoint(30, 0)
            self.setMinimumSize(QtCore.QSize(70, 20))
            self.checked = False

        def paintEvent(self, event):
            super().paintEvent(event)

            painter = QtGui.QPainter(self)

            if self.checked:
                style = QtWidgets.QStyleOptionButton(1)
                style.rect = QtCore.QRect(5, 2, 20, self.size().height() - 4)
                style.state = QtWidgets.QStyle.State_Enabled | QtWidgets.QStyle.State_On

                QtWidgets.QApplication.style().drawPrimitive(
                    QtWidgets.QStyle.PE_IndicatorItemViewItemCheck,
                    style, painter, self
                )

            color = QtGui.QColor(self.color)
            color.setAlphaF(1.0)
            painter.fillRect(
                QtCore.QRect(25, 2, self.size().width() - 30, self.size().height() - 4),
                color
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("project_window")
        self.setWindowTitle("Project")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        self.project.items.added.connect(self._on_item_added)
        self.project.items.removed.connect(self._on_item_removed)
        self.project.items.changed.connect(self._on_item_changed)
        self.project.selection.changed.connect(self._on_project_selection_changed)

        self._updating_selection = False

        self._view = QtWidgets.QListWidget()
        self._view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._view.setEditTriggers(
              QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
        )
        self._view.itemSelectionChanged.connect(
            self._on_list_widget_item_selection_changed)
        self._view.itemChanged.connect(self._on_list_widget_item_changed)

        self.setWidget(self._view)
        for item in self.project.items:
            self._view.addItem(self.ItemWidget(self.project, item))

    def _on_item_added(self, index):
        item = self.project.items[index]
        self._view.insertItem(index, self.ItemWidget(self.project, item))

    def _on_item_removed(self, index):
        self._view.removeItem(index)

    def _on_item_changed(self, index):
        pass

    def _on_project_selection_changed(self):
        if self._updating_selection:
            return

        self._updating_selection = True

        model_index = lambda idx: self._view.model().createIndex(idx, 0)

        selection_model = self._view.selectionModel()
        selection_model.clear()
        for idx in self.project.selection:
            selection_model.select(model_index(idx), QtCore.QItemSelectionModel.Select)

        self._updating_selection = False

    def _on_list_widget_item_selection_changed(self):
        if self._updating_selection:
            return

        self.project.selectedItems = [
            view_item.item
            for view_item in self._view.selectedItems()
        ]

    def _on_list_widget_item_changed(self, item):
        with self.project.items[self._view.row(item)] as view_item:
            view_item.name = item.text()
            view_item.visible = item.checkState() == Qt.Checked

    def _on_context_menu(self, position):
        if self._view.currentItem() is None:
            return

        item = self._view.currentItem().item

        popup = QtWidgets.QMenu(self)

        color_menu = popup.addMenu('Color')
        for color in ITEM_COLORS:
            widget = self.ColorBox(color)
            widget.checked = item.color == color
            set_color_action = QtWidgets.QWidgetAction(self)
            set_color_action.setDefaultWidget(widget)
            set_color_action.triggered.connect(
                (lambda c: lambda _checked: self._set_color(c))(color)
            )
            color_menu.addAction(set_color_action)

        popup.addAction('Delete', self._delete_items)
        if isinstance(item, GerberItem):
            popup.addAction('Create Isolate Job', self._isolate_job)
        elif isinstance(item, ExcellonItem):
            popup.addAction('Create Drill Job', self._drill_job)
        elif isinstance(item, CncJob):
            popup.addAction('Export G-code', self._export_gcode)

        popup.exec(self.mapToGlobal(position))

    def _set_color(self, color):
        GLOBALS.APP.undo_stack.push(SetItemsColorCommand(self.project.selectedItems, color))

    def _delete_items(self):
        GLOBALS.APP.undo_stack.push(DeleteItemsCommand(self.project.selectedItems))

    def _isolate_job(self):
        if len(self.project.selection) == 0:
            return

        command = CreateIsolateJobCommand(self.project.selectedItems[0])
        GLOBALS.APP.undo_stack.push(command)
        GLOBALS.APP.project.selectedItems = [command.result_item]

    def _drill_job(self):
        if len(self.project.selection) == 0:
            return

        command = CreateDrillJobCommand(self.project.selectedItems[0])
        GLOBALS.APP.undo_stack.push(command)
        GLOBALS.APP.project.selectedItems = [command.result_item]

    def _export_gcode(self):
        if len(self.project.selection) == 0:
            return

        result = QtWidgets.QFileDialog.getSaveFileName(
            parent=self, caption='Export Gcode',
            filter='Gerber (*.gcode)',
        )
        if result[0] == '':
            # cancelled
            return

        commands = self.project.selectedItems[0].generate_commands()
        renderer = GcodeRenderer()
        gcode = renderer.render(commands)

        try:
            with open(result[0], 'wt') as f:
                f.write(gcode)
        except Exception as e:
            print('Failed to export Gcode to %s: %s' % (result[0], e))

            info_box = QtWidgets.QMessageBox(self)
            info_box.setWindowTitle('Export Gcode')
            info_box.setText('Failed to export Gcode to %s' % result[0])
            info_box.exec()
