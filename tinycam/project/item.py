from collections.abc import Sequence
from typing import ForwardRef

from tinycam.signals import Signal
from PySide6 import QtGui
from PySide6.QtCore import Qt


class CncProjectItem:
    # Signal whenever any property of an item has changed
    changed = Signal(ForwardRef('CncProjectItem'))

    # Signal used to signal when asynchronous operation on the item has finished
    #
    # E.g. if changing parameter of a job that causes expensive computations,
    # first changed signal will be emitted to signal that the property has changed.
    # When asynchronous update will finish, updated signal will be emitted, so that
    # e.g. UI can update item geometry.
    updated = Signal(ForwardRef('CncProjectItem'))

    def __init__(self, name, color: QtGui.QColor = Qt.black):  # pyright: ignore[reportAttributeAccessIssue]
        self._name = name
        self._color = color
        self._visible = True
        self._debug = False
        self._selected = False
        self._parent = None
        self._children = CncProjectItemCollection(self)

        self._updating = False
        self._updated = False

    def _update(self):
        pass

    def clone(self) -> 'CncProjectItem':
        clone = self.__class__(self.name, self.color)
        clone.visible = self.visible
        clone.selected = self.selected
        # TODO: clone children?
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

    @property
    def parent(self) -> 'CncProjectItem | None':
        return self._parent

    @parent.setter
    def parent(self, value: 'CncProjectItem | None'):
        if self._parent == value:
            return
        self._parent = value
        self._signal_changed()

    @property
    def children(self) -> 'CncProjectItemCollection':
        return self._children


class CncProjectItemCollection:
    added = Signal(CncProjectItem)
    removed = Signal(CncProjectItem)
    changed = Signal(CncProjectItem)
    updated = Signal(CncProjectItem)

    def __init__(self, owner: CncProjectItem | None = None):
        self._owner = owner
        self._items = []
        self._item_changed_callbacks = {}

    def insert(self, index: int, item: CncProjectItem):
        if index < 0:
            index += len(self)
            if index < 0:
                raise KeyError()

        self._items.insert(index, item)
        item.parent = self._owner

        self.added.emit(item)

        item.changed.connect(self._on_item_changed)
        item.updated.connect(self._on_item_updated)

    def append(self, item: CncProjectItem):
        self._items.append(item)
        item.parent = self._owner

        self.added.emit(item)

        item.changed.connect(self._on_item_changed)
        item.updated.connect(self._on_item_updated)

    def extend(self, items: Sequence[CncProjectItem]):
        for item in items:
            self.append(item)

    def remove(self, item: CncProjectItem):
        item.changed.disconnect(self._on_item_changed)
        item.updated.disconnect(self._on_item_updated)
        self._items.remove(item)
        self.removed.emit(item)
        if item.parent == self._owner:
            item.parent = None

    def clear(self):
        for i in reversed(range(len(self))):
            del self[i]

    def index(self, item: CncProjectItem) -> int:
        return self._items.index(item)

    def __iter__(self):
        yield from self._items

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int):
        return self._items[index]

    def __setitem__(self, index: int, item: CncProjectItem):
        if index < 0:
            index += len(self)
            if index < 0:
                raise KeyError()

        old_item = self._items[index]
        if old_item.parent == self._owner:
            old_item.parent = None
        old_item.changed.disconnect(self._on_item_changed)
        old_item.updated.disconnect(self._on_item_updated)

        self._items[index] = item
        item.parent = self._owner
        item.changed.connect(self._on_item_changed)
        item.updated.connect(self._on_item_updated)

        self.removed.emit(old_item)
        self.added.emit(item)

    def __delitem__(self, index: int):
        if index < 0:
            index += len(self)
            if index < 0:
                raise KeyError()

        item = self._items[index]
        if item.parent == self._owner:
            item.parent = None
        item.changed.disconnect(self._on_item_changed)
        item.updated.disconnect(self._on_item_updated)
        del self._items[index]
        self.removed.emit(item)

    def __contains__(self, item: CncProjectItem):
        return item in self._items

    def _on_item_changed(self, item: CncProjectItem):
        index = self._items.index(item)
        if index == -1:
            return
        self.changed.emit(item)

    def _on_item_updated(self, item: CncProjectItem):
        index = self._items.index(item)
        if index == -1:
            return
        self.updated.emit(item)
