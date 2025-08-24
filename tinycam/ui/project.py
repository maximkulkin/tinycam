from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QItemSelection, QSignalBlocker, Qt, QEvent, QAbstractItemModel, QModelIndex
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget, QStyleOptionViewItem
from typing import cast

from tinycam.gcode import GcodeRenderer
from tinycam.globals import GLOBALS
from tinycam.project import CncProject, CncProjectItem, ExcellonItem, GerberItem, CncJob
from tinycam.ui.window import CncWindow
from tinycam.ui.commands import (
    CreateIsolateJobCommand,
    CreateDrillJobCommand,
    CreateCutoutJobCommand,
    DeleteItemsCommand,
    DuplicateItemCommand,
    UpdateItemsCommand,
)
from tinycam.ui.utils import load_icon
from tinycam.utils import index_if


ITEM_COLORS = [
    QtGui.QColor.fromRgbF(0.6, 0.0, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.6, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.0, 0.6, 0.6),
    QtGui.QColor.fromRgbF(0.6, 0.0, 0.6, 0.6),
    QtGui.QColor.fromRgbF(0.6, 0.6, 0.0, 0.6),
    QtGui.QColor.fromRgbF(0.0, 0.6, 0.6, 0.6),
]


class ProjectModel(QAbstractItemModel):
    def __init__(self, project: CncProject, parent=None):
        super().__init__(parent)
        self._project = project
        self._project.items.added.connect(self._on_item_added)
        self._project.items.removed.connect(self._on_item_removed)
        self._project.items.changed.connect(self._on_item_changed)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)

        if not index.parent().isValid():
            return flags

        if index.column() in [0, 2]:
            flags |= Qt.ItemFlag.ItemIsEditable

        return flags

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not parent.isValid():
            if row > 0:
                return QModelIndex()

            return self.createIndex(row, column, self._project)

        item = cast(CncProjectItem, parent.internalPointer())
        if row < 0 or row > len(item.children):
            return QModelIndex()

        return self.createIndex(row, column, item.children[row])

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        item = cast(CncProjectItem, index.internalPointer())
        parent = item.parent
        if parent is None:
            return QModelIndex()

        if parent.parent is None:
            return self.createIndex(0, 0, parent)

        row = parent.parent.children.index(parent)
        if row == -1:
            return QModelIndex()

        return self.createIndex(row, 0, parent)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            # Top level
            return 1

        item = cast(CncProjectItem, parent.internalPointer())
        return len(item.children)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 3

    def data(
        self,
        index: QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if not index.isValid():
            return None

        if role not in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return None

        item = cast(CncProjectItem, index.internalPointer())
        if not index.parent().isValid():
            # Root
            if index.column() == 0:
                return item.name

            return None
        else:
            match index.column():
                case 0: return item.color
                case 1: return item.visible
                case 2: return item.name
                case _: return None

    def setData(self, index: QModelIndex, value: object, role: Qt.ItemDataRole):
        if not index.isValid():
            return False

        if role not in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return False

        item = cast(CncProjectItem, index.internalPointer())
        if not index.parent().isValid():
            return False

        match index.column():
            case 0:
                GLOBALS.APP.undo_stack.push(UpdateItemsCommand([item], {'color': value}))
            case 1:
                item.visible = value
            case 2:
                GLOBALS.APP.undo_stack.push(UpdateItemsCommand([item], {'name': value}))

        return True

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole) -> object:
        return None

    def canDropMimeData(
        self,
        data: object,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if not parent.isValid():
            # Items are not allowed to be dropped to top level
            return False

        return super().canDropMimeData(data, action, row, column, parent)

    def _on_item_added(self, item: CncProjectItem):
        parent = item.parent
        if parent is None:
            parent_index = QModelIndex()
            idx = 0
        else:
            parent_index = self.createIndex(
                0 if parent.parent is None else parent.parent.children.index(parent),
                0,
                parent
            )
            idx = parent.children.index(item)

        if idx >= 0:
            self.beginInsertRows(parent_index, idx, idx)
            self.endInsertRows()

    def _on_item_removed(self, item: CncProjectItem):
        parent = item.parent
        if parent is None:
            parent_index = QModelIndex()
        else:
            parent_index = self.createIndex(
                0 if parent.parent is None else parent.parent.children.index(parent),
                0,
                parent
            )

        row_count = self.rowCount(parent_index)
        self.beginRemoveRows(parent_index, row_count, row_count + 1)
        self.endRemoveRows()

    def _on_item_changed(self, item: CncProjectItem):
        parent = item.parent
        if parent is None:
            idx = 0
        else:
            idx = parent.children.index(item)

        if idx >= 0:
            index_start = self.createIndex(idx, 0, item)
            index_end = self.createIndex(idx, 3, item)
            self.dataChanged.emit(index_start, index_end, [Qt.ItemDataRole.DisplayRole])


class VisibleStyleDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visible_icon = load_icon('icons/eye-open.svg')
        self._invisible_icon = load_icon('icons/eye-closed.svg')

    def paint(self, painter: QtGui.QPainter, option, index):
        if not index.parent().isValid():
            # Root
            super().paint(painter, option, index)
            return

        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

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


class ColorBox(QtWidgets.QWidget):

    def __init__(self, color: QtGui.QColor, **kwargs):
        super().__init__(**kwargs)

        self._color = color
        self._checked = False

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)

        rect = QtCore.QRectF(2, 2, self.width() - 4, self.height() - 4)
        painter.fillRect(rect, self._color)

        painter.end()

    @property
    def color(self) -> QtGui.QColor:
        return self._color

    @color.setter
    def color(self, value: QtGui.QColor):
        self._color = value
        self.update()

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(40, 20)


class ColorBoxItem(ColorBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._checked = False
        self._active = False

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, value: bool):
        self._checked = value
        self.update()

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool):
        self._active = value
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        palette = self.palette()
        bg_color = palette.window() if not self.active else palette.highlight()
        rect = QtCore.QRectF(0, 0, self.width(), self.height())
        painter.fillRect(rect, bg_color)
        painter.end()

        super().paintEvent(event)

        if not self.checked:
            return

        painter = QtGui.QPainter(self)

        size = min(self.width() - 8, self.height() - 8)
        opt = QtWidgets.QStyleOptionButton()
        opt.state = QtWidgets.QStyle.StateFlag.State_On
        opt.rect = QtCore.QRect(
            (self.width() - size) // 2, (self.height() - size) // 2,
            size, size,
        )

        self.style().drawPrimitive(QtWidgets.QStyle.PrimitiveElement.PE_IndicatorMenuCheckMark, opt, painter, self)

        painter.end()


class ColorBoxEditor(ColorBox):
    colorChanged = QtCore.Signal(QtGui.QColor)
    closed = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(color=QtGui.QColor('black'), parent=parent)

        self._popup = QtWidgets.QMenu(self)
        self._popup.setStyleSheet("""
            QMenu {
                padding: 0px;
                margin: 0px;
            }
            QMenu::item {
                padding: 2px 10px;
                margin: 0px;
            }
        """)

        self._popup.aboutToHide.connect(self.closed.emit)

        self.reset()

    def reset(self):
        self._popup.clear()
        for color in ITEM_COLORS:
            self._popup.addAction(self._make_action(color))

        self._custom_color_action = QtGui.QAction('Custom', self._popup)
        self._custom_color_action.triggered.connect(self._pick_color)
        self._popup.addAction(self._custom_color_action)

    @property
    def color(self) -> QtGui.QColor:
        return self._color

    @color.setter
    def color(self, value: QtGui.QColor):
        self._color = value

        idx = index_if(ITEM_COLORS, lambda c: c == self._color)
        if idx == -1:
            action = self._make_action(self._color)
            self._popup.insertAction(self._custom_color_action, action)
        else:
            action = self._popup.actions()[idx]

        action.defaultWidget().checked = True
        self._popup.setActiveAction(action)

    def popup(self, pos: QtCore.QPointF):
        self._popup.exec(pos)

    def _set_color(self, color: QtGui.QColor):
        self._color = color
        self.colorChanged.emit(self._color)

    def _make_action(self, color: QtGui.QColor) -> QtWidgets.QWidgetAction:
        action = QtWidgets.QWidgetAction(self._popup)
        action.setDefaultWidget(ColorBoxItem(color))
        action.triggered.connect(lambda: self._set_color(color))
        return action

    def _pick_color(self):
        original_color = self._color

        self._custom_color_dialog = QtWidgets.QColorDialog()
        self._custom_color_dialog.setCurrentColor(original_color)

        def reject():
            self._set_color(original_color)
            self._custom_color_dialog.close()

        self._custom_color_dialog.currentColorChanged.connect(self._set_color)
        self._custom_color_dialog.rejected.connect(reject)

        QtCore.QTimer.singleShot(0, self._custom_color_dialog.open)


class ColorBoxStyleDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self):
        super().__init__()

        self._editor = ColorBoxEditor()
        self._editor.colorChanged.connect(lambda _: self._on_color_changed())
        self._editor.closed.connect(self._on_closed)

    def createEditor(
        self,
        parent: QWidget | None,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ):
        self._editor.reset()
        self._editor_index = index

        pos = parent.mapToGlobal(option.rect.topLeft())

        QtCore.QTimer.singleShot(0, lambda: self._editor.popup(pos))

        return self._editor

    def destroyEditor(self, editor: QWidget, index: QModelIndex):
        # Do not destroy editor, reuse it
        pass

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        color_editor = cast(ColorBoxEditor, editor)
        color_editor.color = index.data(Qt.ItemDataRole.DisplayRole)

    def setModelData(self, editor, model: QAbstractItemModel, index: QModelIndex):
        color_editor = cast(ColorBoxEditor, editor)
        index.model().setData(index, color_editor.color, Qt.ItemDataRole.DisplayRole)

    def _on_color_changed(self):
        self._editor_index.model().setData(self._editor_index, self._editor.color, Qt.ItemDataRole.DisplayRole)
        self.closeEditor.emit(self._editor, QtWidgets.QItemDelegate.EndEditHint.NoHint)

    def _on_closed(self):
        self.closeEditor.emit(self._editor, QtWidgets.QItemDelegate.EndEditHint.NoHint)

    def helpEvent(self, event, view, option, index):
        if event.type() == QEvent.Type.ToolTip:
            QtWidgets.QToolTip.showText(event.globalPos(), 'Item color', view)
            return True
        return super().helpEvent(event, view, option, index)

    def paint(self, painter: QtGui.QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        if not index.parent().isValid():
            super().paint(painter, option, index)
            return

        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

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

        self.project.selection.changed.connect(self._on_project_selection_changed)

        self._model = ProjectModel(self.project)

        self._view = QtWidgets.QTreeView()
        self._view.setModel(self._model)

        self._view.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self._view.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self._view.header().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self._view.header().setStretchLastSection(False)
        self._view.header().hide()

        self._view.setColumnWidth(0, 60)
        self._view.setColumnWidth(1, 25)
        self._view.setFirstColumnSpanned(0, QModelIndex(), True)

        self._view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._view.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self._view.setDragEnabled(True)
        self._view.setAcceptDrops(True)
        self._view.setDropIndicatorShown(True)
        self._view.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._view.setItemsExpandable(True)
        self._view.setRootIsDecorated(True)

        self._view_visible_delegate = VisibleStyleDelegate()
        self._view_color_delegate = ColorBoxStyleDelegate()
        self._view.setItemDelegateForColumn(0, self._view_color_delegate)
        self._view.setItemDelegateForColumn(1, self._view_visible_delegate)

        self._view.setEditTriggers(
              QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked
            | QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._view.selectionModel().selectionChanged.connect(
            self._on_view_selection_changed
        )

        self.setWidget(self._view)

        self._view.expandAll()

    def _on_project_selection_changed(self):
        selection_model = self._view.selectionModel()

        with QSignalBlocker(selection_model):
            selection_model.clear()

            for item in self.project.selection:
                index = self.project.items.index(item)
                selection_model.select(
                    self._model.createIndex(index, 0, item),
                    QtCore.QItemSelectionModel.SelectionFlag.Select
                    | QtCore.QItemSelectionModel.SelectionFlag.Rows
                )

        self._view.viewport().update()

    def _on_view_selection_changed(self, _selected: QItemSelection, _deselected: QItemSelection):
        self.project.selection.set([
            self.project.items[index.row()]
            for index in self._view.selectedIndexes()
            if index.parent().isValid()
        ])

    def _on_context_menu(self, position: QtCore.QPoint):
        if self._view.currentIndex() is None:
            return

        item = self.project.items[self._view.currentIndex().row()]

        popup = QtWidgets.QMenu(self)

        hide_action = QtGui.QAction('Hide')
        hide_action.triggered.connect(lambda: self._toggle_item_visibility(item))
        hide_action.setCheckable(True)
        hide_action.setChecked(not item.visible)
        popup.addAction(hide_action)

        debug_action = QtGui.QAction('Debug')
        debug_action.triggered.connect(lambda: self._debug_item(item))
        debug_action.setCheckable(True)
        debug_action.setChecked(item.debug)
        popup.addAction(debug_action)

        popup.addSeparator()

        popup.addAction('Duplicate',
                        lambda: self._duplicate_item(item))
        popup.addAction('Delete', self._delete_items)

        popup.addSeparator()
        if isinstance(item, GerberItem):
            popup.addAction('Create Isolate Job', self._isolate_job)
        elif isinstance(item, ExcellonItem):
            popup.addAction('Create Drill Job', self._drill_job)
        elif isinstance(item, CncJob):
            popup.addAction('Export G-code', self._export_gcode)
        elif isinstance(item, CncProjectItem):
            popup.addAction('Create Cutout Job', self._cutout_job)

        popup.exec(self.mapToGlobal(position))

    def _toggle_item_visibility(self, item: CncProjectItem):
        GLOBALS.APP.undo_stack.push(
            UpdateItemsCommand([item], {'visible': not item.visible})
        )

    def _debug_item(self, item: CncProjectItem):
        GLOBALS.APP.undo_stack.push(UpdateItemsCommand([item], {'debug': not item.debug}))

    def _duplicate_item(self, item: CncProjectItem):
        GLOBALS.APP.undo_stack.push(DuplicateItemCommand(item))

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

    def _cutout_job(self):
        if len(self.project.selection) == 0:
            return

        command = CreateCutoutJobCommand(self.project.selection[0])
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
