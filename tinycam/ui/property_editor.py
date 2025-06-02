import typing

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from tinycam.ui.utils import clear_layout
from tinycam import properties
from tinycam.properties import (
    Property, StringProperty, BoolProperty, IntProperty, FloatProperty,
    Vector2Property, Vector3Property,
    get_property_metadata,
)
from tinycam.types import Vector2, Vector3


TYPE_EDITORS = {}


def editor_for(type: type):
    def decorator(klass):
        TYPE_EDITORS[type] = klass
        return klass
    return decorator


@editor_for(str)
class StringPropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(str)

    def __init__(self, target: object, attr: str, parent=None):
        super().__init__(parent)

        self._target = target
        self._attr = attr

        metadata = properties.get_metadata(self._target, self._attr)

        self._editor = QtWidgets.QLineEdit(self)
        self._editor.textChanged.connect(self._on_value_changed)
        self._editor.setReadOnly(metadata.find(properties.ReadOnly) is not None)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._editor)
        self.setLayout(layout)

        self.refreshValue()

    def value(self) -> str:
        return self._editor.text()

    def setValue(self, value: str):
        self._editor.setText(value)

    def refreshValue(self):
        self.setValue(getattr(self._target, self._attr))

    def _on_value_changed(self, value: str):
        setattr(self._target, self._attr, value)
        self.valueChanged.emit(value)


@editor_for(bool)
class BoolPropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(bool)

    def __init__(self, target: object, attr: str, parent=None):
        super().__init__(parent)

        self._target = target
        self._attr = attr

        metadata = properties.get_metadata(self._target, self._attr)

        self._editor = QtWidgets.QCheckBox(self)
        self._editor.checkStateChanged.connect(self._on_value_changed)
        self._editor.setReadOnly(metadata.find(properties.ReadOnly) is not None)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._editor)
        self.setLayout(layout)

        self.refreshValue()

    def value(self) -> bool:
        return self._editor.isChecked()

    def setValue(self, value: bool):
        self._editor.setChecked(value)

    def refreshValue(self):
        self.setValue(getattr(self._target, self._attr))

    def _on_value_changed(self, state: Qt.CheckState):
        value = state == Qt.CheckState.Checked
        setattr(self._target, self._attr, value)
        self.valueChanged.emit(value)


@editor_for(int)
class IntPropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(int)

    def __init__(self, target: object, attr: str, parent=None):
        super().__init__(parent)

        self._target = target
        self._attr = attr

        metadata = properties.get_metadata(self._target, self._attr)

        self._editor = QtWidgets.QSpinBox(self)
        self._editor.valueChanged.connect(self._on_value_changed)
        self._editor.setReadOnly(metadata.find(properties.ReadOnly) is not None)

        min_value = metadata.find(properties.MinValue)
        if min_value is not None:
            self._editor.setMinimum(min_value.value)

        max_value = metadata.find(properties.MaxValue)
        if max_value is not None:
            self._editor.setMaximum(max_value.value)

        suffix = metadata.find(properties.Suffix)
        if suffix is not None:
            self._editor.setSuffix(suffix.suffix)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._editor)
        self.setLayout(layout)

        self.refreshValue()

    def value(self) -> int:
        return self._editor.value()

    def setValue(self, value: int):
        self._editor.setValue(value)

    def refreshValue(self):
        self.setValue(getattr(self._target, self._attr))

    def _on_value_changed(self, value: int):
        setattr(self._target, self._attr, value)
        self.valueChanged.emit(value)


@editor_for(float)
class FloatPropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(float)

    def __init__(self, target: object, attr: str, parent=None):
        super().__init__(parent)

        self._target = target
        self._attr = attr

        metadata = properties.get_metadata(self._target, self._attr)

        self._editor = QtWidgets.QDoubleSpinBox(self)
        self._editor.valueChanged.connect(self._on_value_changed)
        self._editor.setReadOnly(metadata.find(properties.ReadOnly) is not None)

        min_value = metadata.find(properties.MinValue)
        if min_value is not None:
            self._editor.setMinimum(min_value.value)

        max_value = metadata.find(properties.MaxValue)
        if max_value is not None:
            self._editor.setMaximum(max_value.value)

        suffix = metadata.find(properties.Suffix)
        if suffix is not None:
            self._editor.setSuffix(suffix.suffix)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._editor)
        self.setLayout(layout)

        self.refreshValue()

    def value(self) -> float:
        return self._editor.value()

    def setValue(self, value: float):
        self._editor.setValue(value)

    def refreshValue(self):
        self.setValue(getattr(self._target, self._attr))

    def _on_value_changed(self, value: float):
        setattr(self._target, self._attr, value)
        self.valueChanged.emit(value)


@editor_for(Vector2)
class Vector2PropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(Vector2)

    def __init__(self, target: object, attr: str, parent=None):
        super().__init__(parent)

        self._target = target
        self._attr = attr

        metadata = properties.get_metadata(self._target, self._attr)
        readonly = metadata.find(properties.ReadOnly) is not None

        self._x_editor = QtWidgets.QDoubleSpinBox(self)
        self._x_editor.setMinimum(-10000.0)
        self._x_editor.setMaximum(10000.0)
        self._x_editor.setReadOnly(readonly)
        self._x_editor.valueChanged.connect(self._on_value_changed)

        self._y_editor = QtWidgets.QDoubleSpinBox(self)
        self._y_editor.setMinimum(-10000.0)
        self._y_editor.setMaximum(10000.0)
        self._y_editor.setReadOnly(readonly)
        self._y_editor.valueChanged.connect(self._on_value_changed)

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

        self.refreshValue()

    def value(self) -> Vector2:
        return Vector2((self._x_editor.value(), self._y_editor.value()))

    def setValue(self, value: Vector2):
        self._x_editor.setValue(value[0])
        self._y_editor.setValue(value[1])

    def refreshValue(self):
        self.setValue(getattr(self._target, self._attr))

    def _on_value_changed(self, _: float):
        value = Vector2((
            self._x_editor.value(),
            self._y_editor.value(),
        ))
        setattr(self._target, self._attr, value)
        self.valueChanged.emit(value)


@editor_for(Vector3)
class Vector3PropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(Vector3)

    def __init__(self, target: object, attr: str, parent=None):
        super().__init__(parent)

        self._target = target
        self._attr = attr

        metadata = properties.get_metadata(self._target, self._attr)
        readonly = metadata.find(properties.ReadOnly) is not None

        self._x_editor = QtWidgets.QDoubleSpinBox(self)
        self._x_editor.setMinimum(-10000.0)
        self._x_editor.setMaximum(10000.0)
        self._x_editor.setReadOnly(readonly)
        self._x_editor.valueChanged.connect(self._on_value_changed)

        self._y_editor = QtWidgets.QDoubleSpinBox(self)
        self._y_editor.setMinimum(-10000.0)
        self._y_editor.setMaximum(10000.0)
        self._y_editor.setReadOnly(readonly)
        self._y_editor.valueChanged.connect(self._on_value_changed)

        self._z_editor = QtWidgets.QDoubleSpinBox(self)
        self._z_editor.setMinimum(-10000.0)
        self._z_editor.setMaximum(10000.0)
        self._z_editor.setReadOnly(readonly)
        self._z_editor.valueChanged.connect(self._on_value_changed)

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

        self.refreshValue()

    def value(self) -> Vector3:
        return Vector3(
            self._x_editor.value(),
            self._y_editor.value(),
            self._z_editor.value(),
        )

    def setValue(self, value: Vector3):
        self._x_editor.setValue(value[0])
        self._y_editor.setValue(value[1])
        self._z_editor.setValue(value[2])

    def refreshValue(self):
        self.setValue(getattr(self._target, self._attr))

    def _on_value_changed(self, _: float):
        value = Vector3(
            self._x_editor.value(),
            self._y_editor.value(),
            self._z_editor.value(),
        )
        setattr(self._target, self._attr, value)
        self.valueChanged.emit(value)


@editor_for(list)
class ListPropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(int)

    def __init__(self, target: object, attr: str, parent=None):
        super().__init__(parent)

        self._target = target
        self._attr = attr

        metadata = properties.get_metadata(self._target, self._attr)

        self._editor = QtWidgets.QSpinBox(self)
        self._editor.valueChanged.connect(self._on_value_changed)
        self._editor.setReadOnly(metadata.find(properties.ReadOnly) is not None)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._editor)
        self.setLayout(layout)

        self.refreshValue()

    def value(self) -> list:
        return self._editor.value()

    def setValue(self, value: list):
        self._editor.setValue(value)

    def refreshValue(self):
        self.setValue(getattr(self._target, self._attr))


class PropertyEditor(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._layout = QtWidgets.QGridLayout()
        self.setLayout(self._layout)

        self._editors = []

        self._target = None

    @property
    def target(self) -> object:
        return self._target

    @target.setter
    def target(self, value: object):
        self._target = value
        self._populate_props(self._target)

    def _populate_props(self, target: object):
        for row in range(self._layout.rowCount()):
            self._layout.setRowStretch(row, 0)
        clear_layout(self._layout)
        self._editors = []

        if target is None:
            return

        property_names = [
            name
            for name in dir(type(target))
            if not name.startswith('_')
        ]

        for name in property_names:
            prop = getattr(type(target), name)
            if not isinstance(prop, (property, properties.Property)):
                continue

            prop_type = self._get_property_type(prop)

            editor_type = TYPE_EDITORS.get(prop_type)
            if editor_type is None:
                continue

            metadata = properties.get_metadata(target, name)
            hidden = metadata.find(properties.Hidden)
            if hidden is not None:
                continue

            label_metadata = metadata.find(properties.Label)
            if label_metadata is not None:
                label = label_metadata.label
            else:
                label = name.replace('_', ' ').capitalize()

            editor = editor_type(target, name)
            self._editors.append(editor)

            row = self._layout.rowCount()
            self._layout.addWidget(
                QtWidgets.QLabel(label),
                row,
                0,
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            )
            self._layout.addWidget(
                editor,
                row,
                1,
            )

        self._layout.setRowStretch(self._layout.rowCount(), 1)

    def _get_property_type(self, prop: object) -> type:
        if hasattr(prop, 'fget'):
            prop_type = typing.get_type_hints(prop.fget)['return']
        else:
            prop_type = typing.get_type_hints(prop.__get__)['return']

        if isinstance(prop_type, typing.TypeVar):
            for base in prop.__orig_bases__:
                origin = typing.get_origin(base)
                args = typing.get_args(base)
                if origin is not None and hasattr(origin, '__parameters__'):
                    tvar_map = dict(zip(origin.__parameters__, args))
                    prop_type = tvar_map.get(prop_type, prop_type)

        return prop_type

    def _update_editor_values(self):
        for editor in self._editors:
            editor.refreshValue()
