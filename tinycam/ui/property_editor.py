from typing import cast

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from tinycam.ui.utils import clear_layout
from tinycam.properties import (
    Property, StringProperty, BoolProperty, IntProperty, FloatProperty,
    Vector2Property, Vector3Property,
)
from tinycam.types import Vector2, Vector3


class StringPropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(str)

    def __init__(self, target: object, prop: Property, parent=None):
        super().__init__(parent)

        self._target = target
        self._prop = prop

        self._editor = QtWidgets.QLineEdit(self)
        self._editor.textChanged.connect(self._on_value_changed)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._editor)
        self.setLayout(layout)

        self.refreshValue()

    def value(self) -> str:
        return self._editor.text()

    def setValue(self, value: str):
        self._editor.setText(value)

    def refreshValue(self):
        self.setValue(getattr(self._target, self._prop.name))

    def _on_value_changed(self, value: str):
        setattr(self._target, self._prop.name, value)
        self.valueChanged.emit(value)


class BoolPropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(bool)

    def __init__(self, target: object, prop: Property, parent=None):
        super().__init__(parent)

        self._target = target
        self._prop = prop

        self._editor = QtWidgets.QCheckBox(self)
        self._editor.stateChanged.connect(self._on_value_changed)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._editor)
        self.setLayout(layout)

        self.refreshValue()

    def value(self) -> bool:
        return self._editor.isChecked()

    def setValue(self, value: bool):
        self._editor.setChecked(value)

    def refreshValue(self):
        self.setValue(getattr(self._target, self._prop.name))

    def _on_value_changed(self, state: Qt.CheckState):
        value = state == Qt.CheckState.Checked
        setattr(self._target, self._prop.name, value)
        self.valueChanged.emit(value)


class IntPropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(int)

    def __init__(self, target: object, prop: Property, parent=None):
        super().__init__(parent)

        self._target = target
        self._prop = cast(IntProperty, prop)

        self._editor = QtWidgets.QSpinBox(self)
        self._editor.valueChanged.connect(self._on_value_changed)
        if self._prop.min_value is not None:
            self._editor.setMinimum(self._prop.min_value)
        if self._prop.max_value is not None:
            self._editor.setMaximum(self._prop.max_value)
        if self._prop.suffix is not None:
            self._editor.setSuffix(self._prop.suffix)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._editor)
        self.setLayout(layout)

        self.refreshValue()

    def value(self) -> int:
        return self._editor.value()

    def setValue(self, value: int):
        self._editor.setValue(value)

    def refreshValue(self):
        self.setValue(getattr(self._target, self._prop.name))

    def _on_value_changed(self, value: int):
        setattr(self._target, self._prop.name, value)
        self.valueChanged.emit(value)


class FloatPropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(float)

    def __init__(self, target: object, prop: Property, parent=None):
        super().__init__(parent)

        self._target = target
        self._prop = cast(FloatProperty, prop)

        self._editor = QtWidgets.QDoubleSpinBox(self)
        self._editor.valueChanged.connect(self._on_value_changed)
        if self._prop.min_value is not None:
            self._editor.setMinimum(self._prop.min_value)
        if self._prop.max_value is not None:
            self._editor.setMaximum(self._prop.max_value)
        if self._prop.suffix is not None:
            self._editor.setSuffix(self._prop.suffix)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._editor)
        self.setLayout(layout)

        self.refreshValue()

    def value(self) -> float:
        return self._editor.value()

    def setValue(self, value: float):
        self._editor.setValue(value)

    def refreshValue(self):
        self.setValue(getattr(self._target, self._prop.name))

    def _on_value_changed(self, value: float):
        setattr(self._target, self._prop.name, value)
        self.valueChanged.emit(value)


class Vector2PropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(Vector2)

    def __init__(self, target: object, prop: Property, parent=None):
        super().__init__(parent)

        self._target = target
        self._prop = cast(Vector2Property, prop)

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

        self.refreshValue()

    def value(self) -> Vector2:
        return Vector2((self._x_editor.value(), self._y_editor.value()))

    def setValue(self, value: Vector2):
        self._x_editor.setValue(value[0])
        self._y_editor.setValue(value[1])

    def refreshValue(self):
        self.setValue(getattr(self._target, self._prop.name))

    def _on_value_changed(self, _: float):
        value = Vector2((
            self._x_editor.value(),
            self._y_editor.value(),
        ))
        setattr(self._target, self._prop.name, value)
        self.valueChanged.emit(value)


class Vector3PropertyEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(Vector3)

    def __init__(self, target: object, prop: Property, parent=None):
        super().__init__(parent)

        self._target = target
        self._prop = cast(Vector3Property, prop)

        self._x_editor = QtWidgets.QDoubleSpinBox(self)
        self._x_editor.setMinimum(-10000.0)
        self._x_editor.setMaximum(10000.0)
        self._x_editor.valueChanged.connect(self._on_value_changed)

        self._y_editor = QtWidgets.QDoubleSpinBox(self)
        self._y_editor.setMinimum(-10000.0)
        self._y_editor.setMaximum(10000.0)
        self._y_editor.valueChanged.connect(self._on_value_changed)

        self._z_editor = QtWidgets.QDoubleSpinBox(self)
        self._z_editor.setMinimum(-10000.0)
        self._z_editor.setMaximum(10000.0)
        self._z_editor.valueChanged.connect(self._on_value_changed)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel('X:'))
        layout.addWidget(self._x_editor)
        layout.addWidget(QtWidgets.QLabel('Y:'))
        layout.addWidget(self._y_editor)
        layout.addWidget(QtWidgets.QLabel('Z:'))
        layout.addWidget(self._z_editor)
        layout.setStretch(1, 1)
        layout.setStretch(3, 1)
        layout.setStretch(5, 1)
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
        self.setValue(getattr(self._target, self._prop.name))

    def _on_value_changed(self, _: float):
        value = Vector3(
            self._x_editor.value(),
            self._y_editor.value(),
            self._z_editor.value(),
        )
        setattr(self._target, self._prop.name, value)
        self.valueChanged.emit(value)


class PropertyEditor(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._layout = QtWidgets.QGridLayout()
        self._widget = QtWidgets.QWidget()
        self._widget.setLayout(self._layout)

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

        props = [
            prop
            for name in dir(target)
            for prop in [target.__class__.__dict__.get(name, None)]
            if isinstance(prop, Property)
        ]

        for prop in props:
            span = False
            match prop:
                case StringProperty():
                    editor = StringPropertyEditor(target, prop)
                case BoolProperty():
                    editor = BoolPropertyEditor(target, prop)
                case IntProperty():
                    editor = IntPropertyEditor(target, prop)
                case FloatProperty():
                    editor = FloatPropertyEditor(target, prop)
                case Vector2Property():
                    editor = Vector2PropertyEditor(target, prop)
                    span = True
                case Vector3Property():
                    editor = Vector3PropertyEditor(target, prop)
                    span = True
                case _:
                    editor = None

            if editor is None:
                continue

            self._editors.append(editor)

            row = self._layout.rowCount()
            if span:
                self._layout.addWidget(QtWidgets.QLabel(prop.label), row, 0, 1, 2, Qt.AlignLeft)
                layout = QtWidgets.QHBoxLayout()
                layout.addWidget(editor)
                self._layout.addLayout(layout, row + 1, 0, 1, 2, Qt.AlignJustify)
            else:
                self._layout.addWidget(QtWidgets.QLabel(prop.label), row, 0)
                self._layout.addWidget(editor, row, 1)

        self._layout.setRowStretch(self._layout.rowCount(), 1)

    def _update_editor_values(self):
        for editor in self._editors:
            editor.refreshValue()
