from typing import override

from PySide6 import QtCore, QtWidgets

from tinycam.types import Vector2, Vector3


class PushButton(QtWidgets.QPushButton):
    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        options = QtWidgets.QStyleOptionButton();
        self.initStyleOption(options)
        options.rect = self.rect().adjusted(0, -2, 0, -2)
        painter.drawControl(QtWidgets.QStyle.CE_PushButton, options)


class SpinBox(QtWidgets.QSpinBox):
    value_changed = QtCore.Signal(int)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        super().valueChanged.connect(self._on_value_changed)
        self.editingFinished.connect(self._on_editing_finished)
        self.lineEdit().textEdited.connect(self._on_text_edited)

        self._typing = False

    def _on_value_changed(self, value: int):
        if self._typing:
            return

        self.value_changed.emit(self.value())

    def _on_text_edited(self, text: str):
        self._typing = True

    def _on_editing_finished(self):
        if not self._typing:
            return

        self._typing = False
        self.value_changed.emit(self.value())


class DoubleSpinBox(QtWidgets.QDoubleSpinBox):
    value_changed = QtCore.Signal(float)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        super().valueChanged.connect(self._on_value_changed)
        self.editingFinished.connect(self._on_editing_finished)
        self.lineEdit().textEdited.connect(self._on_text_edited)

        self._typing = False

    def _on_value_changed(self, _: float):
        if self._typing:
            return

        self.value_changed.emit(self.value())

    def _on_text_edited(self, _: str):
        self._typing = True

    def _on_editing_finished(self):
        if not self._typing:
            return

        self._typing = False
        self.value_changed.emit(self.value())


class Vector2Editor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(Vector2)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)

        self._value = Vector2()

        self._x_editor = DoubleSpinBox(self)
        self._x_editor.setMinimum(-10000.0)
        self._x_editor.setMaximum(10000.0)
        self._x_editor.value_changed.connect(self._on_value_changed)

        self._y_editor = DoubleSpinBox(self)
        self._y_editor.setMinimum(-10000.0)
        self._y_editor.setMaximum(10000.0)
        self._y_editor.value_changed.connect(self._on_value_changed)

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
        self.setTabOrder(self._x_editor, self._y_editor)

    def value(self) -> Vector2:
        return self._value

    def setValue(self, value: Vector2):
        self._value = value
        self._x_editor.setValue(value[0])
        self._y_editor.setValue(value[1])

    @override
    def setEnabled(self, value: bool):
        super().setEnabled(value)
        self._x_editor.setEnabled(self.enabled())
        self._y_editor.setEnabled(self.enabled())

    def _on_value_changed(self, _: float):
        value = Vector2((
            self._x_editor.value(),
            self._y_editor.value(),
        ))

        if value == self._value:
            return

        self.valueChanged.emit(value)


class Vector3Editor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(Vector3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._value = Vector3()

        self._x_editor = DoubleSpinBox(self)
        self._x_editor.setMinimum(-10000.0)
        self._x_editor.setMaximum(10000.0)
        self._x_editor.value_changed.connect(self._on_value_changed)

        self._y_editor = DoubleSpinBox(self)
        self._y_editor.setMinimum(-10000.0)
        self._y_editor.setMaximum(10000.0)
        self._y_editor.value_changed.connect(self._on_value_changed)

        self._z_editor = DoubleSpinBox(self)
        self._z_editor.setMinimum(-10000.0)
        self._z_editor.setMaximum(10000.0)
        self._z_editor.value_changed.connect(self._on_value_changed)

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
        self.setTabOrder(self._x_editor, self._y_editor)
        self.setTabOrder(self._y_editor, self._z_editor)

    def value(self) -> Vector3:
        return Vector3(
            self._x_editor.value(),
            self._y_editor.value(),
            self._z_editor.value(),
        )

    def setValue(self, value: Vector3):
        self._value = value
        self._x_editor.setValue(value[0])
        self._y_editor.setValue(value[1])
        self._z_editor.setValue(value[2])

    @override
    def setEnabled(self, value: bool):
        super().setEnabled(value)
        self._x_editor.setEnabled(self.enabled())
        self._y_editor.setEnabled(self.enabled())
        self._z_editor.setEnabled(self.enabled())

    def _on_value_changed(self, _: float):
        value = Vector3(
            self._x_editor.value(),
            self._y_editor.value(),
            self._z_editor.value(),
        )
        if value == self._value:
            return

        self.valueChanged.emit(value)
