from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt

from tinycam.globals import GLOBALS


class CncProjectItem(QtCore.QObject):
    changed: QtCore.Signal
    updated: QtCore.Signal

    def __init__(self, name, color: QtGui.QColor = Qt.black):  # pyright: ignore[reportAttributeAccessIssue]
        super().__init__()
        self._name = name
        self._color = color
        self._visible = True
        self._debug = False
        self._selected = False
        self._updating = False
        self._updated = False

    def _update(self):
        pass

    def clone(self) -> 'CncProjectItem':
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

    def _signal_changed(self):
        if self._updating:
            self._updated = True
        else:
            self.changed.emit(self)

    def _signal_updated(self):
        self.updated.emit(self)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        if self._name == value:
            return
        self._name = value
        self._signal_changed()

    @property
    def color(self) -> QtGui.QColor:
        return self._color

    @color.setter
    def color(self, value: QtGui.QColor):
        if self._color == value:
            return
        self._color = value
        self._signal_changed()

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        if self._visible == value:
            return
        self._visible = value
        self._signal_changed()

    @property
    def debug(self) -> bool:
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        if self._debug == value:
            return
        self._debug = value
        self._signal_changed()

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool):
        if self._selected == value:
            return
        self._selected = value
        self._signal_changed()

    def contains(self, point: QtCore.QPoint | QtCore.QPointF):
        return GLOBALS.GEOMETRY.contains(self._geometry, (point.x(), point.y()))


CncProjectItem.changed = QtCore.Signal(CncProjectItem)
CncProjectItem.updated = QtCore.Signal(CncProjectItem)
