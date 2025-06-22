import enum
from dataclasses import dataclass
from functools import partial
from typing import Type, override

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from tinycam.ui.utils import clear_layout
from tinycam import properties as p
from tinycam.types import Vector2, Vector3
from tinycam.utils import get_property_type


TYPE_EDITORS = {}


def editor_for(type: type):
    def decorator(klass):
        TYPE_EDITORS[type] = klass
        return klass
    return decorator


def get_editor_for(type: type) -> type | None:
    def score(editor_type: type) -> int:
        if not issubclass(type, editor_type):
            return 1000
        return type.__mro__.index(editor_type)

    editor_type = min(TYPE_EDITORS.keys(), key=score)
    if not issubclass(type, editor_type):
        return None

    return TYPE_EDITORS[editor_type]


class BasePropertyEditor[T](QtWidgets.QWidget):
    valueChanged = QtCore.Signal(object)

    def __init__(self, t: type, metadata: p.Metadata | None = None, parent=None):
        super().__init__(parent)

        self._type = t
        self._metadata = metadata or p.Metadata()

    @property
    def type(self) -> type:
        return self._type

    def value(self) -> T:
        raise NotImplementedError()

    def setValue(self, value: T):
        raise NotImplementedError()


@editor_for(str)
class StringPropertyEditor(BasePropertyEditor[str]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._editor = QtWidgets.QLineEdit(self)
        self._editor.textChanged.connect(self.valueChanged.emit)
        self._editor.setReadOnly(self._metadata.has(p.ReadOnly))

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)
        self.setLayout(layout)

    @override
    def value(self) -> str:
        return self._editor.text()

    @override
    def setValue(self, value: str):
        self._editor.setText(value)


@editor_for(bool)
class BoolPropertyEditor(BasePropertyEditor[bool]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._editor = QtWidgets.QCheckBox(self)
        self._editor.checkStateChanged.connect(
            lambda state: self.valueChanged.emit(state == Qt.CheckState.Checked)
        )
        self._editor.setEnabled(not self._metadata.has(p.ReadOnly))

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)
        self.setLayout(layout)

    @override
    def value(self) -> bool:
        return self._editor.isChecked()

    @override
    def setValue(self, value: bool):
        self._editor.setChecked(value)


@editor_for(int)
class IntPropertyEditor(BasePropertyEditor[int]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._editor = QtWidgets.QSpinBox(self)
        self._editor.editingFinished.connect(self._on_editing_finished)
        self._editor.setReadOnly(self._metadata.has(p.ReadOnly))

        min_value = self._metadata.find(p.MinValue)
        self._editor.setMinimum(min_value.value if min_value is not None else -1000000)

        max_value = self._metadata.find(p.MaxValue)
        self._editor.setMaximum(max_value.value if max_value is not None else 1000000)

        suffix = self._metadata.find(p.Suffix)
        if suffix is not None:
            self._editor.setSuffix(suffix.formatted_suffix)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)
        self.setLayout(layout)

    @override
    def value(self) -> int:
        return self._editor.value()

    @override
    def setValue(self, value: int):
        self._editor.setValue(value)

    def _on_editing_finished(self):
        self.valueChanged.emit(self._editor.value())


@editor_for(float)
class FloatPropertyEditor(BasePropertyEditor[float]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._editor = QtWidgets.QDoubleSpinBox(self)
        self._editor.editingFinished.connect(self._on_editing_finished)
        self._editor.setReadOnly(self._metadata.has(p.ReadOnly))

        min_value = self._metadata.find(p.MinValue)
        self._editor.setMinimum(min_value.value if min_value is not None else -1000000.0)

        max_value = self._metadata.find(p.MaxValue)
        self._editor.setMaximum(max_value.value if max_value is not None else 1000000.0)

        suffix = self._metadata.find(p.Suffix)
        if suffix is not None:
            self._editor.setSuffix(suffix.formatted_suffix)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)
        self.setLayout(layout)

    @override
    def value(self) -> float:
        return self._editor.value()

    @override
    def setValue(self, value: float):
        self._editor.setValue(value)

    def _on_editing_finished(self):
        self.valueChanged.emit(self._editor.value())


@editor_for(Vector2)
class Vector2PropertyEditor(BasePropertyEditor[Vector2]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        readonly = self._metadata.has(p.ReadOnly)

        self._x_editor = QtWidgets.QDoubleSpinBox(self)
        self._x_editor.setMinimum(-10000.0)
        self._x_editor.setMaximum(10000.0)
        self._x_editor.setReadOnly(readonly)
        self._x_editor.editingFinished.connect(self._on_editing_finished)

        self._y_editor = QtWidgets.QDoubleSpinBox(self)
        self._y_editor.setMinimum(-10000.0)
        self._y_editor.setMaximum(10000.0)
        self._y_editor.setReadOnly(readonly)
        self._y_editor.editingFinished.connect(self._on_editing_finished)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        row1 = QtWidgets.QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.addWidget(QtWidgets.QLabel('X:'))
        row1.addWidget(self._x_editor)
        row2 = QtWidgets.QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.addWidget(QtWidgets.QLabel('Y:'))
        row2.addWidget(self._y_editor)
        row1.setStretch(1, 1)
        row2.setStretch(1, 1)
        layout.addLayout(row1)
        layout.addLayout(row2)
        self.setLayout(layout)

    @override
    def value(self) -> Vector2:
        return Vector2((self._x_editor.value(), self._y_editor.value()))

    @override
    def setValue(self, value: Vector2):
        self._x_editor.setValue(value[0])
        self._y_editor.setValue(value[1])

    def _on_editing_finished(self):
        value = Vector2((
            self._x_editor.value(),
            self._y_editor.value(),
        ))
        self.valueChanged.emit(value)


@editor_for(Vector3)
class Vector3PropertyEditor(BasePropertyEditor[Vector3]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        readonly = self._metadata.has(p.ReadOnly)

        self._x_editor = QtWidgets.QDoubleSpinBox(self)
        self._x_editor.setMinimum(-10000.0)
        self._x_editor.setMaximum(10000.0)
        self._x_editor.setReadOnly(readonly)
        self._x_editor.editingFinished.connect(self._on_editing_finished)

        self._y_editor = QtWidgets.QDoubleSpinBox(self)
        self._y_editor.setMinimum(-10000.0)
        self._y_editor.setMaximum(10000.0)
        self._y_editor.setReadOnly(readonly)
        self._y_editor.editingFinished.connect(self._on_editing_finished)

        self._z_editor = QtWidgets.QDoubleSpinBox(self)
        self._z_editor.setMinimum(-10000.0)
        self._z_editor.setMaximum(10000.0)
        self._z_editor.setReadOnly(readonly)
        self._z_editor.editingFinished.connect(self._on_editing_finished)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        row1 = QtWidgets.QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.addWidget(QtWidgets.QLabel('X:'))
        row1.addWidget(self._x_editor)
        row2 = QtWidgets.QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.addWidget(QtWidgets.QLabel('Y:'))
        row2.addWidget(self._y_editor)
        row3 = QtWidgets.QHBoxLayout()
        row3.setContentsMargins(0, 0, 0, 0)
        row3.addWidget(QtWidgets.QLabel('Z:'))
        row3.addWidget(self._z_editor)
        row1.setStretch(1, 1)
        row2.setStretch(1, 1)
        row3.setStretch(1, 1)
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)
        self.setLayout(layout)

    @override
    def value(self) -> Vector3:
        return Vector3(
            self._x_editor.value(),
            self._y_editor.value(),
            self._z_editor.value(),
        )

    @override
    def setValue(self, value: Vector3):
        self._x_editor.setValue(value[0])
        self._y_editor.setValue(value[1])
        self._z_editor.setValue(value[2])

    def _on_editing_finished(self):
        value = Vector3(
            self._x_editor.value(),
            self._y_editor.value(),
            self._z_editor.value(),
        )
        self.valueChanged.emit(value)


@editor_for(enum.Enum)
class EnumPropertyEditor(BasePropertyEditor[enum.Enum]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        assert issubclass(self._type, enum.Enum)

        self._editor = QtWidgets.QComboBox(self)
        self._editor.setEnabled(not self._metadata.has(p.ReadOnly))
        for value in self._type:
            self._editor.addItem(str(value), userData=value)
        self._editor.currentIndexChanged.connect(self._on_current_index_changed)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)
        self.setLayout(layout)

    @override
    def value(self) -> enum.Enum:
        return self._editor.currentData()

    @override
    def setValue(self, value: enum.Enum):
        index = self._editor.findData(value)
        self._editor.setCurrentIndex(index)

    def _on_current_index_changed(self, index: int):
        value = self._editor.itemData(index)
        self.valueChanged.emit(value)


@editor_for(p.ReferenceType)
class ReferencePropertyEditor(BasePropertyEditor[p.ReferenceType]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._editor = QtWidgets.QComboBox()
        self._editor.addItem('', userData=None)
        for obj in self.type.all_instances():
            self._editor.addItem(str(obj), userData=obj)
        self._editor.currentIndexChanged.connect(self._on_current_index_changed)
        self._editor.setCurrentIndex(0)

        self._updating = False

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)
        self.setLayout(layout)

    @override
    def value(self) -> object:
        return self._editor.currentData()

    @override
    def setValue(self, value: object):
        index = self._editor.findData(value)
        self._updating = True
        self._editor.setCurrentIndex(index)
        self._updating = False

    def _on_current_index_changed(self, index: int):
        if self._updating:
            return

        value = self._editor.itemData(index)
        self.valueChanged.emit(value)


# @editor_for(list)
# class ListPropertyEditor(BasePropertyEditor[list]):
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#
#         self._editor = QtWidgets.QSpinBox(self)
#         self._editor.valueChanged.connect(self._on_value_changed)
#
#         layout = QtWidgets.QHBoxLayout()
#         layout.addWidget(self._editor)
#         self.setLayout(layout)
#
#     @override
#     def value(self) -> list:
#         return self._editor.value()
#
#     @override
#     def setValue(self, value: list):
#         self._editor.setValue(value)


@editor_for(object)
class ObjectPropertyEditor(BasePropertyEditor[object]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._layout = QtWidgets.QGridLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self._editors = {}

        self._value = None

    @override
    def value(self) -> object:
        return self._value

    @override
    def setValue(self, value: object):
        if value is self._value:
            return

        if self._value is not None:
            self._value.changed.disconnect(self._on_value_changed)

        self._value = value
        if self._value is not None:
            self._value.changed.connect(self._on_value_changed)

        self._populate_props()

    def _on_value_changed(self, _: object):
        for name, editor in self._editors.items():
            editor.setValue(getattr(self._value, name))

    def _populate_props(self):
        # TODO: reuse previous editors
        for row in range(self._layout.rowCount()):
            self._layout.setRowStretch(row, 0)
        clear_layout(self._layout)
        self._editors = {}

        if self._value is None:
            return

        target_type = type(self._value)
        property_names = p.get_all(target_type)

        for name in property_names:
            prop = getattr(target_type, name)
            prop_type = get_property_type(prop)

            editor_type = get_editor_for(prop_type)
            if editor_type is None:
                print(f'No editor for type {prop_type}')
                continue

            metadata = p.get_metadata(target_type, name)
            if metadata is None:
                print(f'No property metadata for {name!r}')
                continue

            visible_if = metadata.find(p.VisibleIf)
            if visible_if is not None and not visible_if.condition(self._value):
                continue

            label_metadata = metadata.find(p.Label)
            if label_metadata is not None:
                label = label_metadata.label
            else:
                label = name.replace('_', ' ').capitalize()

            editor = editor_type(prop_type, metadata=metadata)
            self._editors[name] = editor

            editor.setValue(getattr(self._value, name))
            editor.valueChanged.connect(partial(self._on_property_value_changed, name))

            row = self._layout.rowCount()
            label = QtWidgets.QLabel(label)
            self._layout.addWidget(
                label,
                row,
                0,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            )
            self._layout.addWidget(
                editor,
                row,
                1,
                Qt.AlignmentFlag.AlignTop,
            )

        self._layout.setRowStretch(self._layout.rowCount(), 1)

    def _on_property_value_changed(self, name: str, value: object):
        setattr(self._value, name, value)
        self._populate_props()
        self.valueChanged.emit(self._value)


@dataclass
class Editor:
    editor: Type[BasePropertyEditor]


class PropertyEditor(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._target = None
        self._editor = None

        self.setLayout(QtWidgets.QVBoxLayout())

    @property
    def target(self) -> object:
        return self._target

    @target.setter
    def target(self, value: object):
        if self._target is value:
            return

        self._target = value
        if self._editor is not None:
            self.layout().removeWidget(self._editor)
            self._editor.setValue(None)
            self._editor.setParent(None)
            self._editor.deleteLater()
            self._editor = None

        if self._target is not None:
            target_type = type(self._target)
            metadata = p.get_metadata(target_type)

            editor_type = get_editor_for(target_type)

            self._editor = editor_type(target_type, metadata=metadata)
            self.layout().addWidget(self._editor)

            self._editor.setValue(self._target)
