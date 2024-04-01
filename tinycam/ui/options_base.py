from PySide6 import QtCore, QtWidgets

from tinycam.globals import GLOBALS


class StringEdit(QtWidgets.QLineEdit):
    value_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editingFinished.connect(self.value_changed.emit)

    @property
    def value(self):
        return self.text()

    @value.setter
    def value(self, value):
        self.setText(value)


class IntEdit(QtWidgets.QSpinBox):
    value_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self):
        self.value_changed.emit()


class FloatEdit(QtWidgets.QDoubleSpinBox):
    value_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.setValue(self._last_value)
        self.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self):
        self.value_changed.emit()


class Vector2Edit(QtWidgets.QWidget):
    value_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel('X'))
        self._x_edit = FloatEdit(self)
        layout.addWidget(self._x_edit)
        layout.addWidget(QtWidgets.QLabel('Y'))
        self._y_edit = FloatEdit(self)
        layout.addWidget(self._y_edit)
        self.setLayout(layout)

        self._x_edit.value_changed.connect(self.value_changed.emit)
        self._y_edit.value_changed.connect(self.value_changed.emit)

    @property
    def value(self):
        return (float(self._x_edit.text()), float(self._y_edit.text()))

    @value.setter
    def value(self, value):
        self._x_edit.setText(str(value[0]))
        self._y_edit.setText(str(value[1]))

    def _on_value_changed(self, s):
        self.value_changed.emit()


class CncOptionsView(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._items = []
        layout = QtWidgets.QFormLayout()
        # layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.hide()

    def matches(self):
        return False

    def activate(self):
        for item in self._items:
            item.changed.connect(self._on_item_changed)
            self._items.append(item)

        self.update()
        GLOBALS.APP.project.selection.changed.connect(self._on_selection_changed)
        self.show()

    def deactivate(self):
        for item in self._items:
            item.changed.disconnect(self._on_item_changed)

        GLOBALS.APP.project.selection.changed.disconnect(self._on_selection_changed)
        self.hide()

    def update(self):
        pass

    def _on_item_changed(self, item):
        self._update()

    def _on_selection_changed(self):
        for item in self._items:
            item.changed.disconnect(self._on_selection_changed)

        self._items = GLOBALS.APP.project.selectedItems

        for item in self._items:
            item.changed.connect(self._on_selection_changed)

    def _add_label(self, text):
        label = QtWidgets.QLabel(text)
        self.layout().addRow(label)
        return label

    def _add_custom_edit(self, label, widget):
        self.layout().addRow(label, widget)
        return widget

    def _add_string_edit(self, label):
        return self._add_custom_edit(label, StringEdit())

    def _add_int_edit(self, label):
        return self._add_custom_edit(label, IntEdit())

    def _add_float_edit(self, label):
        return self._add_custom_edit(label, FloatEdit())

    def _add_vector_edit(self, label):
        return self._add_custom_edit(label, Vector2Edit())
