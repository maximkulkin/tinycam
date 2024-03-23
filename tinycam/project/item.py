from PySide6 import QtCore
from PySide6.QtCore import Qt


class CncProjectItem(QtCore.QObject):

    def __init__(self, name, color=Qt.black):
        super().__init__()
        self._name = name
        self._color = color
        self._visible = True
        self._selected = False
        self._updating = False
        self._updated = False

    def clone(self):
        clone = self.__class__(self.name, self.color)
        clone.visible = self.visible
        clone.selected = self.selected
        return clone

    def __enter__(self):
        self._updating = True
        self._updated = False
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._updating = False
        if self._updated:
            self.changed.emit(self)

    def _changed(self):
        if self._updating:
            self._updated = True
        else:
            self.changed.emit(self)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if self._name == value:
            return
        self._name = value
        self._changed()

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        if self._color == value:
            return
        self._color = value
        self._changed()

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        if self._visible == value:
            return
        self._visible = value
        self._changed()

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        if self._selected == value:
            return
        self._selected = value
        self._changed()

    def draw(self, painter):
        pass

CncProjectItem.changed = QtCore.Signal(CncProjectItem)


