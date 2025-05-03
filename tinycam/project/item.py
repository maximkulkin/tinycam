from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt


class CncProjectItem(QtCore.QObject):
    # Signal whenever any property of an item has changed
    changed: QtCore.Signal

    # Signal used to signal when asynchronous operation on the item has finished
    #
    # E.g. if changing parameter of a job that causes expensive computations,
    # first changed signal will be emitted to signal that the property has changed.
    # When asynchronous update will finish, updated signal will be emitted, so that
    # e.g. UI can update item geometry.
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
        """A context to withhold update events for an item if multiple updates are planned

        Example:

            with item:
                item.color = color1
                item.visible = True

        """
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


CncProjectItem.changed = QtCore.Signal(CncProjectItem)
CncProjectItem.updated = QtCore.Signal(CncProjectItem)
