from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QEvent, QAbstractItemModel, QModelIndex
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget, QStyleOptionViewItem
from typing import cast

from tinycam.gcode import GcodeRenderer
from tinycam.globals import GLOBALS
from tinycam.project import CncProjectItem, ExcellonItem, GerberItem, CncJob
from tinycam.ui.window import CncWindow
from tinycam.ui.commands import (
    CreateIsolateJobCommand,
    CreateDrillJobCommand,
    DeleteItemsCommand,
    UpdateItemsCommand,
)


ITEM_COLORS = [
    QtGui.QColor.fromRgbF(0.6, 0.0, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.6, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.0, 0.6, 0.6),
    QtGui.QColor.fromRgbF(0.6, 0.0, 0.6, 0.6),
    QtGui.QColor.fromRgbF(0.6, 0.6, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.6, 0.6, 0.6),
]


class ProjectItemModel(QtGui.QStandardItemModel):
    def flags(self, index):
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )


class VisibleStyleDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visible_icon = self._load_icon('icons/eye-open.svg')
        self._invisible_icon = self._load_icon('icons/eye-closed.svg')

    def _load_icon(self, path):
        img = QtGui.QPixmap(path)
        painter = QtGui.QPainter(img)
        painter.setCompositionMode(
            QtGui.QPainter.CompositionMode.CompositionMode_SourceIn
        )
        painter.fillRect(img.rect(), QtGui.QColor('white'))
        painter.end()
        return QtGui.QIcon(img)

    def paint(self, painter: QtGui.QPainter, option, index):
        visible = index.data(Qt.ItemDataRole.DisplayRole)

        if visible:
            icon = self._visible_icon
        else:
            icon = self._invisible_icon

        rect = QtCore.QRect(option.rect)
        rect.adjust(4, 4, -4, -4)

        icon.paint(painter, rect, Qt.AlignmentFlag.AlignCenter)

    def createEditor(self, parent, option, index):
        return None

    def editorEvent(self, event, model, option, index):
        if (event.type() == QEvent.Type.MouseButtonPress and
                cast(QMouseEvent, event).button() == Qt.MouseButton.LeftButton):
            model.setData(
                index,
                not index.data(Qt.ItemDataRole.DisplayRole),
                Qt.ItemDataRole.DisplayRole,
            )
            model.dataChanged.emit(index, index)
            return True
        return False

    def helpEvent(self, event, view, option, index):
        if event.type() == QEvent.Type.ToolTip:
            QtWidgets.QToolTip.showText(event.globalPos(), 'Show / Hide', view)
            return True
        return super().helpEvent(event, view, option, index)


class DebugStyleDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._debug_enabled_icon = self._load_icon('icons/debug-view.svg')
        self._debug_disabled_icon = self._load_icon('icons/debug-view.svg', QtGui.QColor('grey'))

    def _load_icon(self, path, color=QtGui.QColor('white')):
        img = QtGui.QPixmap(path)
        painter = QtGui.QPainter(img)
        painter.setCompositionMode(
            QtGui.QPainter.CompositionMode.CompositionMode_SourceIn
        )
        painter.fillRect(img.rect(), color)
        painter.end()
        return QtGui.QIcon(img)

    def paint(self, painter, option, index):
        debug = index.data(Qt.ItemDataRole.DisplayRole)

        icon = self._debug_enabled_icon if debug else self._debug_disabled_icon

        rect = QtCore.QRect(option.rect)
        rect.adjust(4, 4, -4, -4)

        icon.paint(painter, rect, Qt.AlignmentFlag.AlignCenter)

    def createEditor(self, parent, option, index):
        return None

    def editorEvent(self, event, model, option, index):
        if (event.type() == QEvent.Type.MouseButtonPress and
                cast(QMouseEvent, event).button() == Qt.MouseButton.LeftButton):
            model.setData(index, not index.data(Qt.ItemDataRole.DisplayRole), Qt.ItemDataRole.DisplayRole)
            model.dataChanged.emit(index, index)
            return True
        return False

    def helpEvent(self, event, view, option, index):
        if event.type() == QEvent.Type.ToolTip:
            QtWidgets.QToolTip.showText(event.globalPos(), 'Debug view', view)
            return True
        return super().helpEvent(event, view, option, index)


class CheckboxStyleDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        checked = index.data(Qt.ItemDataRole.DisplayRole)

        style = QtWidgets.QApplication.style()
        checkbox_option = QtWidgets.QStyleOptionButton()
        checkbox_option.state = QtWidgets.QStyle.StateFlag.State_Enabled | (QtWidgets.QStyle.StateFlag.State_On if checked else QtWidgets.QStyle.StateFlag.State_Off)

        rect = style.subElementRect(QtWidgets.QStyle.SubElement.SE_CheckBoxIndicator, option)
        rect.moveCenter(option.rect.center())
        checkbox_option.rect = rect

        style.drawControl(QtWidgets.QStyle.ControlElement.CE_CheckBox, checkbox_option, painter)

    def sizeHint(self, option, index):
        return QtCore.QSize(20, 20)


class ColorComboBoxDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        color = index.data(Qt.ItemDataRole.UserRole)
        if color is not None:
            color = QtGui.QColor(color)
            color.setAlphaF(1.0)
            painter.fillRect(option.rect, color)

        if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
            style = QtWidgets.QStyleOptionButton(1)
            style.rect = option.rect
            style.state = QtWidgets.QStyle.StateFlag.State_Enabled | QtWidgets.QStyle.StateFlag.State_On

            QtWidgets.QApplication.style().drawPrimitive(
                QtWidgets.QStyle.PrimitiveElement.PE_IndicatorCheckBox,
                style, painter
            )


class ColorBoxStyleDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, table_view, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._table_view = table_view
        self._delegate = None

    def createEditor(
        self,
        parent: QWidget | None,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ):
        if self._delegate is None:
            self._delegate = ColorComboBoxDelegate(self)

        editor = QtWidgets.QComboBox(parent)
        editor.setItemDelegate(self._delegate)
        for color in ITEM_COLORS:
            editor.addItem('', color)
        editor.addItem('Custom', None)
        editor.activated.connect(lambda _: self._on_item_changed(editor, index))
        QtCore.QTimer.singleShot(100, editor.showPopup)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        color = index.data(Qt.ItemDataRole.DisplayRole)
        idx = editor.findData(color)
        if idx == -1:
            editor.insertItem(len(ITEM_COLORS), '', color)
            editor.setCurrentIndex(editor.findData(color))
        else:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex):
        color = editor.currentData()
        if color is not None:
            model.setData(index, color, Qt.ItemDataRole.DisplayRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def _on_item_changed(self, editor, index):
        if editor.currentIndex() == editor.count() - 1:
            # QtWidgets.QColorDialog.getColor()
            original_color = index.data(Qt.ItemDataRole.DisplayRole)

            def set_color(color: QtGui.QColor):
                index.model().setData(index, color, Qt.ItemDataRole.DisplayRole)

            self._custom_color_dialog = QtWidgets.QColorDialog()
            self._custom_color_dialog.setCurrentColor(original_color)
            self._custom_color_dialog.currentColorChanged.connect(set_color)

            def reject():
                set_color(original_color)
                self._custom_color_dialog.close()

            self._custom_color_dialog.rejected.connect(reject)
            self._custom_color_dialog.open()
            return

        self._table_view.commitData(editor)
        self._table_view.closeEditor(editor, QtWidgets.QItemDelegate.EndEditHint.NoHint)

    def helpEvent(self, event, view, option, index):
        if event.type() == QEvent.Type.ToolTip:
            QtWidgets.QToolTip.showText(event.globalPos(), 'Item color', view)
            return True
        return super().helpEvent(event, view, option, index)

    def paint(self, painter: QtGui.QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        color = index.data(Qt.ItemDataRole.DisplayRole)
        color = QtGui.QColor(color)
        color.setAlphaF(1.0)
        rect = QtCore.QRect(option.rect)
        rect.adjust(5, 5, -5, -5)
        painter.fillRect(rect, color)

    def sizeHint(self, option, index):
        return QtCore.QSize(60, 20)


class CncProjectWindow(CncWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("project_window")
        self.setWindowTitle("Project")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        self.project.items.added.connect(self._on_item_added)
        self.project.items.removed.connect(self._on_item_removed)
        self.project.items.changed.connect(self._on_item_changed)
        self.project.selection.changed.connect(self._on_project_selection_changed)

        self._updating_selection = False

        self._model = ProjectItemModel(self)
        self._model.setHorizontalHeaderLabels(['', '', '', 'Name'])
        self._model.dataChanged.connect(self._on_model_data_changed)

        self._view = QtWidgets.QTableView(self)
        self._view.setModel(self._model)
        self._view.setColumnWidth(0, 25)
        self._view.setColumnWidth(1, 25)
        self._view.setColumnWidth(2, 60)
        self._view.horizontalHeader().setStretchLastSection(True)
        self._view.horizontalHeader().hide()
        self._view.verticalHeader().hide()
        self._view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._view.setEditTriggers(
              QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked
            | QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._view.selectionModel().selectionChanged.connect(
            self._on_table_view_selection_changed
        )

        self._view_visible_delegate = VisibleStyleDelegate()
        self._view_debug_delegate = DebugStyleDelegate()
        self._view_color_delegate = ColorBoxStyleDelegate(self._view)
        self._view.setItemDelegateForColumn(0, self._view_visible_delegate)
        self._view.setItemDelegateForColumn(1, self._view_debug_delegate)
        self._view.setItemDelegateForColumn(2, self._view_color_delegate)

        self.setWidget(self._view)
        for item in self.project.items:
            self._add_item(item)

    def _add_item(self, item: CncProjectItem):
        visibleItem = QtGui.QStandardItem()
        visibleItem.setData(item.visible, Qt.ItemDataRole.DisplayRole)

        debugItem = QtGui.QStandardItem()
        debugItem.setData(item.debug, Qt.ItemDataRole.DisplayRole)

        colorItem = QtGui.QStandardItem()
        colorItem.setData(item.color, Qt.ItemDataRole.DisplayRole)

        nameItem = QtGui.QStandardItem(item.name)

        items = [visibleItem, debugItem, colorItem, nameItem]
        self._model.appendRow(items)

    def _on_item_added(self, item: CncProjectItem):
        self._add_item(item)

    def _on_item_removed(self, item: CncProjectItem):
        index = self.project.items.index(item)
        self._updating_selection = True
        self._model.removeRow(index)
        self._updating_selection = False

    def _on_item_changed(self, item: CncProjectItem):
        index = self.project.items.index(item)

        self._model.setData(
            self._model.index(index, 0),
            item.visible, Qt.ItemDataRole.DisplayRole
        )
        self._model.setData(
            self._model.index(index, 1),
            item.debug, Qt.ItemDataRole.DisplayRole
        )
        self._model.setData(
            self._model.index(index, 2),
            item.color, Qt.ItemDataRole.DisplayRole
        )
        self._model.setData(
            self._model.index(index, 3),
            item.name, Qt.ItemDataRole.DisplayRole
        )

    def _on_model_data_changed(self, top_left, bottom_right, _roles):
        def get_value(row, col):
            return self._model.data(self._model.index(row, col), Qt.ItemDataRole.DisplayRole)

        for i in range(top_left.row(), bottom_right.row() + 1):
            item = self.project.items[i]
            item.visible = get_value(i, 0)
            item.debug = get_value(i, 1)

            updates = {
                'color': get_value(i, 2),
                'name': get_value(i, 3),
            }
            updates = {
                k: v
                for k, v in updates.items()
                if getattr(item, k) != v
            }
            if updates:
                GLOBALS.APP.undo_stack.push(UpdateItemsCommand([item], updates))

    def _on_project_selection_changed(self):
        if self._updating_selection:
            return

        self._updating_selection = True

        def model_index(idx: int) -> QModelIndex:
            return self._view.model().createIndex(idx, 0)

        selection_model = self._view.selectionModel()
        selection_model.clear()
        for item in self.project.selection:
            idx = self.project.items.index(item)
            selection_model.select(
                model_index(idx),
                QtCore.QItemSelectionModel.SelectionFlag.SelectCurrent
                    | QtCore.QItemSelectionModel.SelectionFlag.Rows
            )

        self._updating_selection = False

    def _on_table_view_selection_changed(self, _selected, _deselected):
        if self._updating_selection:
            return

        self.project.selection.set([
            self.project.items[index.row()]
            for index in self._view.selectedIndexes()
        ])

    def _on_context_menu(self, position: QtCore.QPoint):
        if self._view.currentIndex() is None:
            return

        item = self.project.items[self._view.currentIndex().row()]

        popup = QtWidgets.QMenu(self)

        popup.addAction('Delete', self._delete_items)
        if isinstance(item, GerberItem):
            popup.addAction('Create Isolate Job', self._isolate_job)
        elif isinstance(item, ExcellonItem):
            popup.addAction('Create Drill Job', self._drill_job)
        elif isinstance(item, CncJob):
            popup.addAction('Export G-code', self._export_gcode)

        popup.exec(self.mapToGlobal(position))

    def _delete_items(self):
        GLOBALS.APP.undo_stack.push(DeleteItemsCommand(list(self.project.selection)))

    def _isolate_job(self):
        if len(self.project.selection) == 0:
            return

        command = CreateIsolateJobCommand(self.project.selection[0])
        GLOBALS.APP.undo_stack.push(command)
        if command.result_item is not None:
            GLOBALS.APP.project.selection.set([command.result_item])

    def _drill_job(self):
        if len(self.project.selection) == 0:
            return

        command = CreateDrillJobCommand(self.project.selection[0])
        GLOBALS.APP.undo_stack.push(command)
        if command.result_item is not None:
            GLOBALS.APP.project.selection.set([command.result_item])

    def _export_gcode(self):
        if len(self.project.selection) == 0:
            return

        result = QtWidgets.QFileDialog.getSaveFileName(
            parent=self, caption='Export Gcode',
            dir=f'{self.project.selection[0].name}.gcode',
            filter='Gerber (*.gcode)',
        )
        if result[0] == '':
            # cancelled
            return

        commands = self.project.selection[0].generate_commands()
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
