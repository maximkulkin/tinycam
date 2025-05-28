from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QEvent, QAbstractItemModel, QModelIndex
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


class ProjectModel(QAbstractItemModel):
    def __init__(self, project: CncProject, parent=None):
        super().__init__(parent)
        self._project = project
        self._project.items.added.connect(self._on_item_added)
        self._project.items.removed.connect(self._on_item_removed)
        self._project.items.changed.connect(self._on_item_changed)

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

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        item = cast(CncProjectItem, index.internalPointer())
        if not index.parent().isValid():
            # Root
            if index.column() == 0:
                return item.name

            return None
        else:
            match index.column():
                case 0: return item.name
                case 1: return item.color
                case 2: return item.visible
                case _: return None

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
            idx = 0
        else:
            parent_index = self.createIndex(
                0 if parent.parent is None else parent.parent.children.index(parent),
                0,
                parent
            )
            idx = parent.children.index(item)

        if idx >= 0:
            self.beginRemoveRows(parent_index, idx, idx)
            self.endRemoveRows()

    def _on_item_changed(self, item: CncProjectItem):
        parent = item.parent
        if parent is None:
            idx = 0
        else:
            idx = parent.children.index(item)

        if idx >= 0:
            index = self.createIndex(idx, 0, item)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])


def load_icon(path: str, bg_color: QtGui.QColor = QtGui.QColor('white')) -> QtGui.QIcon:
    img = QtGui.QPixmap(path)
    painter = QtGui.QPainter(img)
    painter.setCompositionMode(
        QtGui.QPainter.CompositionMode.CompositionMode_SourceIn
    )
    painter.fillRect(img.rect(), bg_color)
    painter.end()
    return QtGui.QIcon(img)


class ItemStyleDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visible_icon = load_icon('icons/eye-open.svg')
        self._invisible_icon = load_icon('icons/eye-closed.svg')

    def paint(self, painter: QtGui.QPainter, option, index):
        if not index.parent().isValid():
            return super().paint(painter, option, index)

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


class VisibleStyleDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visible_icon = load_icon('icons/eye-open.svg')
        self._invisible_icon = load_icon('icons/eye-closed.svg')

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
        self._debug_enabled_icon = load_icon('icons/debug-view.svg')
        self._debug_disabled_icon = load_icon('icons/debug-view.svg', QtGui.QColor('grey'))

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

        self.project.selection.changed.connect(self._on_project_selection_changed)

        self._updating_selection = False

        self._model = ProjectModel(self.project)
        # self._model.setHorizontalHeaderLabels(['', '', '', 'Name'])

        self._view = QtWidgets.QTreeView()
        self._view.setModel(self._model)
        # self._view.setColumnWidth(0, 25)
        self._view.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self._view.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self._view.header().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self._view.header().resizeSection(0, 200)
        self._view.header().resizeSection(1, 60)
        self._view.header().resizeSection(2, 25)

        # self._view.setColumnWidth(2, 25)
        # self._view.header().hide()
        # self._view.header().setStretchLastSection(True)

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
        self._view_debug_delegate = DebugStyleDelegate()
        self._view_color_delegate = ColorBoxStyleDelegate(self._view)
        # self._view.setItemDelegateForColumn(0, self._view_visible_delegate)
        # self._view.setItemDelegateForColumn(1, self._view_debug_delegate)
        # self._view.setItemDelegateForColumn(2, self._view_color_delegate)

        # self._view.setEditTriggers(
        #       QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked
        #     | QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed
        # )
        self._view.selectionModel().selectionChanged.connect(
            self._on_view_selection_changed
        )

        self.setWidget(self._view)

        self._view.expandAll()

    def _on_project_selection_changed(self):
        if self._updating_selection:
            return

        self._updating_selection = True

        selection_model = self._view.selectionModel()
        selection_model.clear()
        for item in self.project.selection:
            index = self.project.items.index(item)
            selection_model.select(
                self._model.createIndex(index, 0, item),
                QtCore.QItemSelectionModel.SelectionFlag.Select
                | QtCore.QItemSelectionModel.SelectionFlag.Rows
            )

        self._updating_selection = False

    def _on_view_selection_changed(self, _selected, _deselected):
        if self._updating_selection:
            return

        self.project.selection.set([
            self.project.items[index.row()]
            for index in self._view.selectedIndexes()
            if index.parent().isValid()
        ])

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
