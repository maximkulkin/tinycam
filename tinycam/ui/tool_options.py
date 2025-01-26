from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt

from tinycam.globals import GLOBALS
from tinycam.ui.window import CncWindow
from tinycam.properties import Property, StringProperty, BoolProperty, IntProperty, FloatProperty, Vector2Property
from tinycam.types import Vector2


__all__ = ['CncToolOptionsWindow']


class ObjectPropertiesModel(QtCore.QAbstractItemModel):
    def __init__(self, target: object):
        super().__init__()
        self._target = target
        self._attrs = [
            attr
            for name in dir(self._target)
            for attr in [getattr(self._target.__class__, name, None)]
            if isinstance(attr, Property)
        ]

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._attrs)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None

        if section == 0:
            return 'Name'
        elif section == 1:
            return 'Value'

        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if index.row() >= len(self._attrs):
            return None

        if role == Qt.UserRole:
            return self._attrs[index.row()]

        if index.column() == 0:
            if role != Qt.DisplayRole:
                return None
            return self._attrs[index.row()].label

        elif index.column() == 1:
            value = self._attrs[index.row()].__get__(self._target)
            if role == Qt.DisplayRole:
                return str(value)
            elif role == Qt.EditRole:
                return value

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole:
            return

        if index.parent().isValid() or index.column() != 1 or index.row() >= len(self._attrs):
            return

        self._attrs[index.row()].__set__(self._target, value)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return None

        if row > len(self._attrs) or column >= 2:
            return QtCore.QModelIndex()

        return self.createIndex(row, column, None)

    def parent(self, index):
        return QtCore.QModelIndex()

    def flags(self, index):
        flags = Qt.ItemIsSelectable | Qt.ItemNeverHasChildren | Qt.ItemIsEnabled
        if index.column() == 1:
            flags = flags | Qt.ItemIsEditable
        return flags


class Vector2Editor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(Vector2)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._x_editor = QtWidgets.QDoubleSpinBox(self)
        self._x_editor.setMinimum(-10000.0)
        self._x_editor.setMaximum(10000.0)
        self._x_editor.valueChanged.connect(self._on_value_changed)

        self._y_editor = QtWidgets.QDoubleSpinBox(self)
        self._y_editor.setMinimum(-10000.0)
        self._y_editor.setMaximum(10000.0)
        self._y_editor.valueChanged.connect(self._on_value_changed)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel('X:'))
        layout.addWidget(self._x_editor)
        layout.addWidget(QtWidgets.QLabel('Y:'))
        layout.addWidget(self._y_editor)
        layout.setStretch(1, 1)
        layout.setStretch(3, 1)
        self.setLayout(layout)

    def xEditor(self) -> QtWidgets.QDoubleSpinBox:
        return self._x_editor

    def yEditor(self) -> QtWidgets.QDoubleSpinBox:
        return self._y_editor

    def value(self) -> Vector2:
        return Vector2((self._x_editor.value(), self._y_editor.value()))

    def setValue(self, value: Vector2):
        self._x_editor.setValue(value[0])
        self._y_editor.setValue(value[1])

    def _on_value_changed(self, _: float):
        self.valueChanged.emit(Vector2((self._x_editor.value(), self._y_editor.value())))


class CustomWidgetDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, tree, parent=None):
        super().__init__(parent)
        self._tree: QtWidgets.QTreeView = tree
        self._padding: int = 5

    def sizeHint(self, option, index):
        base_size = super().sizeHint(option, index)
        return QtCore.QSize(
            base_size.width() + 2 * self._padding,
            base_size.height() + 2 * self._padding,
        )

    def paint(self, painter, option, index):
        item_type = index.data(Qt.UserRole)
        if item_type and self._tree.indexWidget(index) is not None:
            return

        padded_rect = option.rect.adjusted(self._padding, self._padding, -self._padding, -self._padding)
        painter.save()

        bg_color = option.palette.highlight() if option.state & QtWidgets.QStyledItemDelegate.State_Selected else option.palette.base()
        painter.fillRect(option.rect, bg_color)

        text = index.data(Qt.DisplayRole)
        painter.drawText(padded_rect, Qt.AlignLeft | Qt.AlignVCenter, text)

        painter.restore()

    def createEditor(self, parent, option, index):
        attr = index.data(Qt.UserRole)
        match attr:
            case StringProperty():
                editor = QtWidgets.QLineEdit(parent)
            case BoolProperty():
                editor = QtWidgets.QCheckBox(parent)
            case IntProperty():
                editor = QtWidgets.QSpinBox(parent)
                if attr.min_value is not None:
                    editor.setMinimum(attr.min_value)
                if attr.max_value is not None:
                    editor.setMaximum(attr.max_value)
                if attr.suffix is not None:
                    editor.setSuffix(attr.suffix)
            case FloatProperty():
                editor = QtWidgets.QDoubleSpinBox(parent)
                if attr.min_value is not None:
                    editor.setMinimum(attr.min_value)
                if attr.max_value is not None:
                    editor.setMaximum(attr.max_value)
                if attr.suffix is not None:
                    editor.setSuffix(attr.suffix)
            case Vector2Property():
                editor = Vector2Editor(parent)
                editor.valueChanged.connect(lambda value: self._on_vector2_value_changed(value, index))
            case _:
                editor = None

        return editor

    def _on_vector2_value_changed(self, value: Vector2, index: QtCore.QModelIndex):
        index.model().setData(index, value, Qt.EditRole)

    def setEditorData(self, editor, index):
        value = index.data(Qt.EditRole)
        if isinstance(editor, QtWidgets.QLineEdit):
            editor.setText(value)

            def deselect():
                editor.deselect()

            QtCore.QTimer.singleShot(0, deselect)
        elif isinstance(editor, QtWidgets.QCheckBox):
            editor.setChecked(bool(value))
        elif isinstance(editor, QtWidgets.QSpinBox):
            editor.setValue(int(value))

            def deselect():
                editor.lineEdit().deselect()

            QtCore.QTimer.singleShot(0, deselect)
        elif isinstance(editor, QtWidgets.QDoubleSpinBox):
            editor.setValue(float(value))

            def deselect():
                editor.lineEdit().deselect()

            QtCore.QTimer.singleShot(0, deselect)

        elif isinstance(editor, QtWidgets.QLabel):
            editor.setText(str(value))

        elif isinstance(editor, Vector2Editor):
            editor.setValue(value)

            def deselect():
                editor.xEditor().lineEdit().deselect()
                editor.yEditor().lineEdit().deselect()

            QtCore.QTimer.singleShot(0, deselect)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QtWidgets.QLineEdit):
            model.setData(index, editor.text(), Qt.EditRole)
        elif isinstance(editor, QtWidgets.QCheckBox):
            model.setData(index, editor.checked(), Qt.EditRole)
        elif isinstance(editor, QtWidgets.QSpinBox):
            model.setData(index, editor.value(), Qt.EditRole)
        elif isinstance(editor, QtWidgets.QDoubleSpinBox):
            model.setData(index, editor.value(), Qt.EditRole)
        elif isinstance(editor, Vector2Editor):
            model.setData(index, editor.value(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        rect = option.rect.adjusted(self._padding, self._padding, -self._padding, -self._padding)
        editor.setGeometry(rect)


class OptionsTreeView(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._delegate = CustomWidgetDelegate(self)
        self.setItemDelegateForColumn(1, self._delegate)
        self.setAlternatingRowColors(True)

    def paintEvent(self, event):
        model = self.model()
        if model is not None:
            for i in range(model.rowCount()):
                index = model.index(i, 1)
                self.openPersistentEditor(index)

        super().paintEvent(event)


class CncToolOptionsWindow(CncWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("tool_options_window")
        self.setWindowTitle("Tool options")

        self._tree = OptionsTreeView(self)
        self.setWidget(self._tree)

        GLOBALS.APP.project.selection.changed.connect(self._on_project_selection_changed)

    def _on_project_selection_changed(self):
        items = list(GLOBALS.APP.project.selection.items())
        if items:
            self._populate_tree(items[0])
        else:
            self._populate_tree(None)

    def _populate_tree(self, target: object):
        self._model = ObjectPropertiesModel(target)
        self._tree.setModel(self._model)
