from typing import override

from PySide6 import QtCore, QtWidgets

from tinycam.types import Vector2


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
